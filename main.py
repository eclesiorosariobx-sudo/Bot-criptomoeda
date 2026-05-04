import telebot
import ccxt
import pandas as pd
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from tradingview_ta import TA_Handler, Interval
import feedparser
import schedule
import time
import threading
import random
import os
import requests
from datetime import datetime, timezone
from flask import Flask, request

# ╔══════════════════════════════════════════════════════════════╗
# ║         CONFIGURAÇÃO — SISTEMA INSTITUCIONAL ELITE          ║
# ╚══════════════════════════════════════════════════════════════╝

TOKEN    = "7734730548:AAHM8SufT9OuA0KoYRGglf24Vm8kQTCrpbA"
CHAT_ID  = "-1003780528406"
WEBHOOK_URL = os.environ.get("RAILWAY_STATIC_URL", "").rstrip("/")

# Ativos monitorados simultaneamente
WATCHLIST = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ╔══════════════════════════════════════════════════════════════╗
# ║                     SABEDORIA ELITE                         ║
# ╚══════════════════════════════════════════════════════════════╝

SABEDORIA = [
"📜 <i>«Vi o crash de 1929, a bolha das dot-com e o colapso de 2008. O mercado sempre pune a ganância e recompensa a paciência.»</i>",
"📜 <i>«Em décadas de operação, aprendi que o stop loss não é fraqueza — é sobrevivência.»</i>",
"📜 <i>«O mercado não é inimigo. É um espelho da psicologia humana. Domine a si mesmo e dominará o mercado.»</i>",
"📜 <i>«Nunca vi um trader consistente que operava por emoção. A frieza é o seu maior ativo.»</i>",
"📜 <i>«Mais importante que o ponto de entrada é saber exatamente onde você está errado antes de entrar.»</i>",
"📜 <i>«A maior lição que aprendi: preserve o capital. Quem sobrevive, eventualmente prospera.»</i>",
"📜 <i>«Ciclos se repetem porque a natureza humana não muda. Estude a história e terá vantagem sobre 95% do mercado.»</i>",
"📜 <i>«Não existe setup perfeito sem gestão de risco perfeita. Um sem o outro é especulação pura.»</i>",
"📜 <i>«Os grandes traders não prevêem o futuro — eles gerenciam probabilidades com disciplina cirúrgica.»</i>",
"📜 <i>«Volume não mente. Quando o preço sobe sem volume, desconfie. Quando cai com volume, respeite.»</i>",
]

MOTIVACOES = [
"💎 <b>O mercado transfere dinheiro dos impacientes para os pacientes.</b>",
"🚀 <b>Traders amadores focam nos lucros. Profissionais focam em proteger o capital.</b>",
"🦅 <b>A disciplina é a ponte entre a meta e a realização.</b>",
"🔥 <b>Um dia ruim de trade não define sua carreira. A consistência, sim.</b>",
"👑 <b>O sucesso no mercado financeiro é 20% estratégia e 80% psicologia.</b>",
"⚔️ <b>O trader que sobrevive ao bear market está preparado para dominar o bull.</b>",
]

# ╔══════════════════════════════════════════════════════════════╗
# ║              ANÁLISE TRADINGVIEW MULTI-TIMEFRAME            ║
# ╚══════════════════════════════════════════════════════════════╝

def get_tradingview_analysis(symbol="BTCUSDT", interval=Interval.INTERVAL_1_HOUR):
	try:
		handler = TA_Handler(
			symbol=symbol,
			screener="crypto",
			exchange="BINANCE",
			interval=interval,
		)
		analysis = handler.get_analysis()
		rec        = analysis.summary["RECOMMENDATION"]
		buy_count  = analysis.summary.get("BUY", 0)
		sell_count = analysis.summary.get("SELL", 0)
		neutral    = analysis.summary.get("NEUTRAL", 0)
		price      = analysis.indicators["close"]
		rsi        = analysis.indicators.get("RSI", 0)
		rsi14      = analysis.indicators.get("RSI[1]", rsi)
		macd       = analysis.indicators.get("MACD.macd", 0)
		macd_sig   = analysis.indicators.get("MACD.signal", 0)
		macd_hist  = macd - macd_sig
		bb_upper   = analysis.indicators.get("BB.upper", 0)
		bb_lower   = analysis.indicators.get("BB.lower", 0)
		bb_mid     = (bb_upper + bb_lower) / 2 if bb_upper and bb_lower else price
		volume     = analysis.indicators.get("volume", 0)
		ema9       = analysis.indicators.get("EMA9",  price)
		ema21      = analysis.indicators.get("EMA21", price)
		ema50      = analysis.indicators.get("EMA50", price)
		ema200     = analysis.indicators.get("EMA200", price)
		adx        = analysis.indicators.get("ADX", 0)
		stoch_k    = analysis.indicators.get("Stoch.K", 50)
		stoch_d    = analysis.indicators.get("Stoch.D", 50)
		atr        = analysis.indicators.get("ATR", 0)

		return {
			"rec": rec, "price": price,
			"buy_count": buy_count, "sell_count": sell_count, "neutral": neutral,
			"rsi": rsi, "rsi14": rsi14,
			"macd": macd, "macd_sig": macd_sig, "macd_hist": macd_hist,
			"bb_upper": bb_upper, "bb_lower": bb_lower, "bb_mid": bb_mid,
			"volume": volume,
			"ema9": ema9, "ema21": ema21, "ema50": ema50, "ema200": ema200,
			"adx": adx, "stoch_k": stoch_k, "stoch_d": stoch_d, "atr": atr,
		}
	except Exception as e:
		print(f"Erro TV ({symbol}): {e}")
		return None

def get_multi_timeframe(symbol="BTCUSDT"):
	tf_map = {
		"15min": Interval.INTERVAL_15_MINUTES,
		"1h":    Interval.INTERVAL_1_HOUR,
		"4h":    Interval.INTERVAL_4_HOURS,
		"1d":    Interval.INTERVAL_1_DAY,
	}
	results = {}
	for label, interval in tf_map.items():
		data = get_tradingview_analysis(symbol, interval)
		if data:
			results[label] = data
		time.sleep(0.3)
	return results

def score_signal(tf_data):
	buy_score = sell_score = 0
	weights = {"15min": 1, "1h": 2, "4h": 3, "1d": 4}

	for label, d in tf_data.items():
		w = weights.get(label, 1)
		rec = d["rec"]
		adx = d.get("adx", 0)
		trend_strength = 1.3 if adx > 25 else 1.0

		if "STRONG_BUY" in rec:
			buy_score += 2 * w * trend_strength
		elif "BUY" in rec:
			buy_score += 1 * w * trend_strength
		elif "STRONG_SELL" in rec:
			sell_score += 2 * w * trend_strength
		elif "SELL" in rec:
			sell_score += 1 * w * trend_strength

		# RSI confirmação
		rsi = d.get("rsi", 50)
		if rsi < 35:
			buy_score += 1 * w
		elif rsi > 65:
			sell_score += 1 * w

		# MACD confirmação
		if d.get("macd_hist", 0) > 0:
			buy_score += 0.5 * w
		elif d.get("macd_hist", 0) < 0:
			sell_score += 0.5 * w

	max_score = 30
	if buy_score > sell_score and buy_score >= 5:
		return min(round((buy_score / max_score) * 10, 1), 10.0), "BUY"
	elif sell_score > buy_score and sell_score >= 5:
		return min(round((sell_score / max_score) * 10, 1), 10.0), "SELL"
	return 0, "NEUTRAL"

# ╔══════════════════════════════════════════════════════════════╗
# ║              SUPORTE E RESISTÊNCIA (PIVOT POINTS)           ║
# ╚══════════════════════════════════════════════════════════════╝

def calculate_support_resistance(symbol="BTC/USDT", timeframe="1d", limit=30):
	try:
		exchange = ccxt.binance()
		bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
		df = pd.DataFrame(bars, columns=["time","open","high","low","close","volume"])

		# Pivot Points Clássicos (último candle fechado)
		last = df.iloc[-2]
		H, L, C = last["high"], last["low"], last["close"]
		P  = (H + L + C) / 3
		R1 = 2 * P - L
		R2 = P + (H - L)
		R3 = H + 2 * (P - L)
		S1 = 2 * P - H
		S2 = P - (H - L)
		S3 = L - 2 * (H - P)

		# Máximas e mínimas relevantes (últimas 30 velas)
		recent_high = df["high"].max()
		recent_low  = df["low"].min()

		return {
			"pivot": P, "r1": R1, "r2": R2, "r3": R3,
			"s1": S1, "s2": S2, "s3": S3,
			"recent_high": recent_high, "recent_low": recent_low,
		}
	except Exception as e:
		print(f"Erro S/R: {e}")
		return None

# ╔══════════════════════════════════════════════════════════════╗
# ║                   DOMINÂNCIA DO BTC                         ║
# ╚══════════════════════════════════════════════════════════════╝

def get_btc_dominance():
	try:
		url = "https://api.coingecko.com/api/v3/global"
		r = requests.get(url, timeout=8)
		data = r.json()
		dominance = data["data"]["market_cap_percentage"]["btc"]
		total_mcap = data["data"]["total_market_cap"]["usd"]
		btc_mcap   = data["data"]["market_cap_percentage"].get("btc", 0)
		eth_dom    = data["data"]["market_cap_percentage"].get("eth", 0)
		return {
			"dominance": round(dominance, 2),
			"total_mcap": total_mcap,
			"eth_dom": round(eth_dom, 2),
		}
	except Exception as e:
		print(f"Erro dominância: {e}")
		return None

# ╔══════════════════════════════════════════════════════════════╗
# ║              GESTÃO DE RISCO AVANÇADA                       ║
# ╚══════════════════════════════════════════════════════════════╝

def calculate_risk_management(price, direction, atr, score):
	"""
	Calcula níveis de entrada, TPs e SL baseados em ATR real.
	Retorna múltiplo R:R para cada TP.
	"""
	# ATR fallback: 1.5% do preço
	if not atr or atr == 0:
		atr = price * 0.015

	atr_mult_sl  = 1.5  # SL = 1.5x ATR
	atr_mult_tp1 = 1.5  # TP1 = 1.5x ATR (1:1 R:R)
	atr_mult_tp2 = 3.0  # TP2 = 3.0x ATR (1:2 R:R)
	atr_mult_tp3 = 5.0  # TP3 = 5.0x ATR (1:3.3 R:R)

	if direction == "BUY":
		sl  = price - (atr * atr_mult_sl)
		tp1 = price + (atr * atr_mult_tp1)
		tp2 = price + (atr * atr_mult_tp2)
		tp3 = price + (atr * atr_mult_tp3)
	else:
		sl  = price + (atr * atr_mult_sl)
		tp1 = price - (atr * atr_mult_tp1)
		tp2 = price - (atr * atr_mult_tp2)
		tp3 = price - (atr * atr_mult_tp3)

	sl_dist  = abs(price - sl)
	rr1 = round(abs(tp1 - price) / sl_dist, 2) if sl_dist else 0
	rr2 = round(abs(tp2 - price) / sl_dist, 2) if sl_dist else 0
	rr3 = round(abs(tp3 - price) / sl_dist, 2) if sl_dist else 0

	# Tamanho sugerido da posição (1% banca / distância ao SL)
	banca_exemplo = 1000  # USDT de exemplo
	risco_por_trade = banca_exemplo * 0.01  # 1% da banca
	position_size = round(risco_por_trade / sl_dist, 6) if sl_dist else 0

	return {
		"sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3,
		"rr1": rr1, "rr2": rr2, "rr3": rr3,
		"atr": atr, "sl_dist": sl_dist,
		"position_size_example": position_size,
	}

# ╔══════════════════════════════════════════════════════════════╗
# ║                   GRÁFICO PREMIUM ELITE                     ║
# ╚══════════════════════════════════════════════════════════════╝

def generate_elite_chart(symbol="BTC/USDT", timeframe="1h", limit=150, levels=None):
	try:
		exchange = ccxt.binance()
		bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
		df = pd.DataFrame(bars, columns=["time","open","high","low","close","volume"])
		df["time"] = pd.to_datetime(df["time"], unit="ms")
		df.set_index("time", inplace=True)

		# ── Cores ──────────────────────────────────────────────
		BG       = "#0B0E1A"
		PANEL    = "#10142A"
		GREEN    = "#00E5A0"
		RED      = "#FF3D6B"
		GOLD     = "#F5C842"
		BLUE     = "#4DA6FF"
		PURPLE   = "#B06EFF"
		TEXT     = "#CDD6F4"
		GRID     = "#1E2440"
		WHITE    = "#FFFFFF"

		fig = plt.figure(figsize=(18, 11), facecolor=BG)
		gs  = GridSpec(4, 1, figure=fig, hspace=0.04,
		               height_ratios=[3.5, 0.8, 0.8, 0.9])

		ax_candle = fig.add_subplot(gs[0])
		ax_vol    = fig.add_subplot(gs[1], sharex=ax_candle)
		ax_rsi    = fig.add_subplot(gs[2], sharex=ax_candle)
		ax_macd   = fig.add_subplot(gs[3], sharex=ax_candle)

		for ax in [ax_candle, ax_vol, ax_rsi, ax_macd]:
			ax.set_facecolor(PANEL)
			ax.tick_params(colors=TEXT, labelsize=8)
			ax.spines[:].set_color(GRID)
			ax.yaxis.label.set_color(TEXT)

		# ── Candles manuais ────────────────────────────────────
		opens  = df["open"].values
		highs  = df["high"].values
		lows   = df["low"].values
		closes = df["close"].values
		xs     = np.arange(len(df))

		for i, (o, h, l, c) in enumerate(zip(opens, highs, lows, closes)):
			color = GREEN if c >= o else RED
			ax_candle.plot([i, i], [l, h], color=color, linewidth=0.8, alpha=0.9)
			ax_candle.bar(i, abs(c - o), bottom=min(o, c),
			              color=color, width=0.7, alpha=0.95)

		# ── EMAs ───────────────────────────────────────────────
		close_s = df["close"]
		ema9  = close_s.ewm(span=9,   adjust=False).mean()
		ema21 = close_s.ewm(span=21,  adjust=False).mean()
		ema50 = close_s.ewm(span=50,  adjust=False).mean()
		ema200= close_s.ewm(span=200, adjust=False).mean()

		ax_candle.plot(xs, ema9.values,   color=GOLD,   linewidth=1.1, label="EMA 9",   alpha=0.85)
		ax_candle.plot(xs, ema21.values,  color=BLUE,   linewidth=1.1, label="EMA 21",  alpha=0.85)
		ax_candle.plot(xs, ema50.values,  color=PURPLE, linewidth=1.1, label="EMA 50",  alpha=0.85)
		ax_candle.plot(xs, ema200.values, color=RED,    linewidth=1.3, label="EMA 200", alpha=0.75, linestyle="--")

		# ── Bollinger Bands ────────────────────────────────────
		bb_mid  = close_s.rolling(20).mean()
		bb_std  = close_s.rolling(20).std()
		bb_up   = bb_mid + 2 * bb_std
		bb_dn   = bb_mid - 2 * bb_std
		ax_candle.fill_between(xs, bb_up.values, bb_dn.values, alpha=0.06, color=BLUE)
		ax_candle.plot(xs, bb_up.values, color=BLUE, linewidth=0.5, alpha=0.4, linestyle=":")
		ax_candle.plot(xs, bb_dn.values, color=BLUE, linewidth=0.5, alpha=0.4, linestyle=":")

		# ── Suporte/Resistência no gráfico ────────────────────
		if levels:
			for key, val, color, lbl in [
				("r2", levels.get("r2"), "#FF6B6B", "R2"),
				("r1", levels.get("r1"), "#FFA07A", "R1"),
				("pivot", levels.get("pivot"), GOLD,    "P"),
				("s1", levels.get("s1"), "#90EE90", "S1"),
				("s2", levels.get("s2"), "#32CD32", "S2"),
			]:
				if val:
					ax_candle.axhline(val, color=color, linewidth=0.8,
					                  linestyle="--", alpha=0.6)
					ax_candle.text(len(xs) - 1, val, f" {lbl}", color=color,
					               fontsize=7, va="center", fontweight="bold")

		# ── Legenda e título ──────────────────────────────────
		legend = ax_candle.legend(loc="upper left", fontsize=7.5,
		                           facecolor="#0B0E1A", edgecolor=GRID,
		                           labelcolor=TEXT, framealpha=0.9)

		now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
		ax_candle.set_title(
			f"  {symbol}  |  Análise Institucional Elite  |  {timeframe.upper()}  |  {now_str}",
			color=WHITE, fontsize=11, fontweight="bold", loc="left", pad=10,
			fontfamily="monospace"
		)
		ax_candle.set_ylabel("Preço (USDT)", color=TEXT, fontsize=8)
		ax_candle.yaxis.set_label_position("right")
		ax_candle.yaxis.tick_right()
		ax_candle.grid(axis="y", color=GRID, linewidth=0.5, alpha=0.6)
		plt.setp(ax_candle.get_xticklabels(), visible=False)

		# ── Volume com cor ────────────────────────────────────
		vol_colors = [GREEN if c >= o else RED for o, c in zip(opens, closes)]
		ax_vol.bar(xs, df["volume"].values, color=vol_colors, alpha=0.7, width=0.7)
		vol_ma = df["volume"].rolling(20).mean()
		ax_vol.plot(xs, vol_ma.values, color=GOLD, linewidth=0.8, alpha=0.7)
		ax_vol.set_ylabel("VOL", color=TEXT, fontsize=7)
		ax_vol.yaxis.set_label_position("right")
		ax_vol.yaxis.tick_right()
		ax_vol.grid(axis="y", color=GRID, linewidth=0.4, alpha=0.5)
		ax_vol.set_yticks([])
		plt.setp(ax_vol.get_xticklabels(), visible=False)

		# ── RSI ───────────────────────────────────────────────
		delta  = close_s.diff()
		gain   = delta.clip(lower=0).rolling(14).mean()
		loss   = (-delta.clip(upper=0)).rolling(14).mean()
		rs     = gain / loss.replace(0, np.nan)
		rsi    = 100 - (100 / (1 + rs))

		ax_rsi.plot(xs, rsi.values, color=PURPLE, linewidth=1.2)
		ax_rsi.axhline(70, color=RED,   linewidth=0.6, linestyle="--", alpha=0.5)
		ax_rsi.axhline(30, color=GREEN, linewidth=0.6, linestyle="--", alpha=0.5)
		ax_rsi.axhline(50, color=GRID,  linewidth=0.4, linestyle=":",  alpha=0.4)
		ax_rsi.fill_between(xs, rsi.values, 70, where=(rsi.values >= 70),
			                 color=RED, alpha=0.15)
		ax_rsi.fill_between(xs, rsi.values, 30, where=(rsi.values <= 30),
			                 color=GREEN, alpha=0.15)
		ax_rsi.set_ylim(0, 100)
		ax_rsi.set_ylabel("RSI", color=TEXT, fontsize=7)
		ax_rsi.yaxis.set_label_position("right")
		ax_rsi.yaxis.tick_right()
		ax_rsi.set_yticks([30, 50, 70])
		ax_rsi.grid(axis="y", color=GRID, linewidth=0.4, alpha=0.5)
		plt.setp(ax_rsi.get_xticklabels(), visible=False)

		# ── MACD ──────────────────────────────────────────────
		ema12  = close_s.ewm(span=12, adjust=False).mean()
		ema26  = close_s.ewm(span=26, adjust=False).mean()
		macd_l = ema12 - ema26
		signal = macd_l.ewm(span=9, adjust=False).mean()
		hist   = macd_l - signal

		hist_colors = [GREEN if v >= 0 else RED for v in hist.values]
		ax_macd.bar(xs, hist.values, color=hist_colors, alpha=0.7, width=0.7)
		ax_macd.plot(xs, macd_l.values, color=BLUE,  linewidth=1.0, label="MACD")
		ax_macd.plot(xs, signal.values, color=GOLD,  linewidth=1.0, label="Signal")
		ax_macd.axhline(0, color=GRID, linewidth=0.5, alpha=0.6)
		ax_macd.set_ylabel("MACD", color=TEXT, fontsize=7)
		ax_macd.yaxis.set_label_position("right")
		ax_macd.yaxis.tick_right()
		ax_macd.grid(axis="y", color=GRID, linewidth=0.4, alpha=0.5)

		# Eixo X com datas
		step = max(1, len(xs) // 10)
		tick_pos = xs[::step]
		tick_lbl = [df.index[i].strftime("%d/%m %Hh") for i in tick_pos]
		ax_macd.set_xticks(tick_pos)
		ax_macd.set_xticklabels(tick_lbl, fontsize=7, color=TEXT)

		# Borda dourada superior
		fig.patches.append(
			mpatches.FancyBboxPatch(
				(0, 0.995), 1, 0.005,
				transform=fig.transFigure, clip_on=False,
				boxstyle="square,pad=0", facecolor=GOLD, edgecolor="none"
			)
		)

		filename = f"elite_chart_{symbol.replace('/', '')}.png"
		plt.savefig(filename, dpi=150, bbox_inches="tight",
		            facecolor=BG, edgecolor="none")
		plt.close(fig)
		return filename

	except Exception as e:
		print(f"Erro ao gerar gráfico elite: {e}")
		return None

# ╔══════════════════════════════════════════════════════════════╗
# ║                   ENVIO DE SINAL ELITE                      ║
# ╚══════════════════════════════════════════════════════════════╝

def send_trade_signal(symbol="BTCUSDT"):
	tf_data = get_multi_timeframe(symbol)
	if not tf_data:
		return

	score, direction = score_signal(tf_data)
	if direction == "NEUTRAL" or score < 5:
		print(f"[{symbol}] Sem sinal relevante (score={score}, dir={direction})")
		return

	d1h = tf_data.get("1h", list(tf_data.values())[0])
	price   = d1h["price"]
	rsi     = d1h["rsi"]
	macd    = d1h["macd"]
	macd_sig= d1h["macd_sig"]
	macd_hist = d1h["macd_hist"]
	adx     = d1h.get("adx", 0)
	stoch_k = d1h.get("stoch_k", 50)
	volume  = d1h["volume"]
	atr     = d1h.get("atr", 0)

	rec_15 = tf_data.get("15min", {}).get("rec", "—")
	rec_1h = tf_data.get("1h",   {}).get("rec", "—")
	rec_4h = tf_data.get("4h",   {}).get("rec", "—")
	rec_1d = tf_data.get("1d",   {}).get("rec", "—")

	# ── Gestão de risco ATR-based ──────────────────────────────
	rm = calculate_risk_management(price, direction, atr, score)

	# ── Suporte/Resistência ────────────────────────────────────
	ccxt_symbol = symbol.replace("USDT", "/USDT")
	levels = calculate_support_resistance(ccxt_symbol)

	# ── Dominância BTC ────────────────────────────────────────
	dom = get_btc_dominance()

	# ── Formatação ────────────────────────────────────────────
	is_buy = direction == "BUY"
	emoji_dir = "🟢" if is_buy else "🔴"
	trade_type = "COMPRA  ▲ LONG" if is_buy else "VENDA   ▼ SHORT"
	chart_emoji = "📈" if is_buy else "📉"

	stars = "★" * min(int(score), 5) + ("✦" if score >= 8 else "")
	quality_lbl = (
		"EXCEPCIONAL ✦✦✦" if score >= 8.5 else
		"ALTA        ✦✦"  if score >= 6.5 else
		"MODERADA    ✦"
	)

	# Contexto RSI
	rsi_ctx = (
		f"\n⚠️ <i>RSI sobrecomprado ({rsi:.1f}) — reduza o tamanho ou aguarde pullback.</i>"
		if rsi > 72 else
		f"\n⚠️ <i>RSI sobrevendido ({rsi:.1f}) — zona de reversão potencial.</i>"
		if rsi < 28 else ""
	)

	# MACD momentum
	macd_ctx = "Acelerando ↑↑" if macd_hist > 0 and macd > macd_sig else \
	           "Enfraquecendo ↓↓" if macd_hist < 0 else "Cruzamento →"

	# ADX força da tendência
	adx_ctx = (
		"Tendência FORTE  🔥" if adx > 35 else
		"Tendência MÉDIA  ⚡" if adx > 20 else
		"Tendência FRACA  💤"
	)

	# Dominância
	dom_txt = ""
	if dom:
		dom_txt = (
			f"\n🌐 <b>Dominância BTC:</b> {dom['dominance']}%  |  ETH: {dom['eth_dom']}%"
		)

	# Suporte/Resistência
	sr_txt = ""
	if levels:
		sr_txt = (
			f"\n{'─'*32}\n"
			f"🧱 <b>SUPORTE &amp; RESISTÊNCIA (Pivot Diário)</b>\n"
			f"   R3 → <code>${levels['r3']:,.2f}</code>\n"
			f"   R2 → <code>${levels['r2']:,.2f}</code>\n"
			f"   R1 → <code>${levels['r1']:,.2f}</code>\n"
			f"   🎯 P → <code>${levels['pivot']:,.2f}</code>\n"
			f"   S1 → <code>${levels['s1']:,.2f}</code>\n"
			f"   S2 → <code>${levels['s2']:,.2f}</code>\n"
			f"   S3 → <code>${levels['s3']:,.2f}</code>"
		)

	now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y • %H:%M UTC")

	mensagem = (
		f"{chart_emoji} <b>SINAL INSTITUCIONAL ELITE</b> {chart_emoji}\n"
		f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n"
		f"🕐 <i>{now_str}</i>\n"
		f"💠 <b>Ativo:</b> #{symbol.replace('USDT','')}/ USDT\n"
		f"{emoji_dir} <b>Operação:</b> <code>{trade_type}</code>\n"
		f"🏆 <b>Qualidade:</b> {stars} {quality_lbl}\n"
		f"🔢 <b>Score Multi-TF:</b> <b>{score}/10</b>\n"
		f"📊 <b>Força da Tendência:</b> {adx_ctx}\n"
		f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n"
		f"💰 <b>ENTRADA (Mercado):</b> <code>${price:,.2f}</code>\n"
		f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n"
		f"✅ <b>TP1 — 33% da posição:</b>  <code>${rm['tp1']:,.2f}</code>  (R:R {rm['rr1']}x)\n"
		f"✅ <b>TP2 — 33% da posição:</b>  <code>${rm['tp2']:,.2f}</code>  (R:R {rm['rr2']}x)\n"
		f"✅ <b>TP3 — 34% da posição:</b>  <code>${rm['tp3']:,.2f}</code>  (R:R {rm['rr3']}x)\n"
		f"❌ <b>STOP LOSS:</b>             <code>${rm['sl']:,.2f}</code>\n"
		f"📐 <b>ATR (volatilidade):</b>    <code>${rm['atr']:,.2f}</code>\n"
		f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n"
		f"📡 <b>CONFIRMAÇÃO MULTI-TIMEFRAME</b>\n"
		f"   • 15min → <i>{rec_15}</i>\n"
		f"   •   1h  → <i>{rec_1h}</i>\n"
		f"   •   4h  → <i>{rec_4h}</i>\n"
		f"   •   1D  → <i>{rec_1d}</i>\n"
		f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n"
		f"📉 <b>RSI (1H):</b>    {rsi:.1f}{rsi_ctx}\n"
		f"⚡ <b>MACD:</b>        {macd_ctx}\n"
		f"🎲 <b>Stoch K:</b>     {stoch_k:.1f}\n"
		f"{dom_txt}"
		f"{sr_txt}\n"
		f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n"
		f"🛡️ <b>GESTÃO DE RISCO</b>\n"
		f"   • Risco máximo recomendado: <b>1% a 2% da banca</b>\n"
		f"   • Distância ao SL: <code>${rm['sl_dist']:,.2f}</code>\n"
		f"   • Escale 33% a cada TP atingido\n"
		f"   • Mova SL para entrada após TP1\n"
		f"   • Nunca opere sem stop definido\n"
		f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n"
		f"\n{random.choice(SABEDORIA)}"
	)

	chart_file = generate_elite_chart(ccxt_symbol, levels=levels)

	try:
		def enviar_mensagem_segura(msg):
    msg = msg.replace("<div>", "").replace("</div>", "")
    partes = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
    for parte in partes:
        bot.send_message(CHAT_ID, parte, parse_mode="HTML")

try:
    if chart_file and os.path.exists(chart_file):
        with open(chart_file, "rb") as photo:
            bot.send_photo(CHAT_ID, photo, caption="📊 Gráfico do sinal")
        os.remove(chart_file)

        enviar_mensagem_segura(mensagem)

    else:
        enviar_mensagem_segura(mensagem)

    print(f"[{symbol}] Sinal enviado — score={score}, dir={direction}")

except Exception as e:
    print(f"Erro ao enviar sinal [{symbol}]: {e}")
		print(f"[{symbol}] Sinal enviado — score={score}, dir={direction}")
	except Exception as e:
		print(f"Erro ao enviar sinal [{symbol}]: {e}")

def scan_all_assets():
	"""Varre toda a watchlist e envia sinais encontrados."""
	for symbol in WATCHLIST:
		send_trade_signal(symbol)
		time.sleep(2)

# ╔══════════════════════════════════════════════════════════════╗
# ║                RADAR DE NOTÍCIAS ELITE                      ║
# ╚══════════════════════════════════════════════════════════════╝

def send_crypto_news():
	feeds = [
		"https://cointelegraph.com.br/rss",
		"https://livecoins.com.br/feed/",
	]
	entries = []
	for url in feeds:
		try:
			feed = feedparser.parse(url)
			if feed.entries:
				entries.append(feed.entries[0])
		except:
			pass

	if not entries:
		return

	dom = get_btc_dominance()
	dom_txt = ""
	if dom:
		dom_txt = (
			f"\n🌐 <b>Dominância BTC:</b> {dom['dominance']}%  "
			f"|  Market Cap Total: ${dom['total_mcap']/1e12:.2f}T"
		)

	entry = random.choice(entries)
	summary = entry.get("summary", "")[:250]
	mensagem = (
		"🌍 <b>RADAR DO MERCADO — ELITE NEWS</b> 🌍\n"
		f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n"
		f"📰 <b>{entry.title}</b>\n\n"
		f"<i>{summary}…</i>\n\n"
		f"🔗 <a href=\"{entry.link}\">Ler matéria completa →</a>\n"
		f"{dom_txt}\n"
		f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n"
		f"💡 {random.choice(MOTIVACOES)}\n\n"
		f"{random.choice(SABEDORIA)}"
	)
	try:
		bot.send_message(CHAT_ID, mensagem, disable_web_page_preview=False)
	except Exception as e:
		print(f"Erro ao enviar notícias: {e}")

# ╔══════════════════════════════════════════════════════════════╗
# ║              RESUMO DIÁRIO DO MERCADO                       ║
# ╚══════════════════════════════════════════════════════════════╝

def send_daily_summary():
	dom = get_btc_dominance()
	dom_txt = ""
	if dom:
		mcap_t = dom["total_mcap"] / 1e12
		dom_txt = (
			f"🌐 <b>Dominância BTC:</b> {dom['dominance']}%\n"
			f"💼 <b>Market Cap Total:</b> ${mcap_t:.2f}T\n"
			f"🔷 <b>Dominância ETH:</b>  {dom['eth_dom']}%\n"
		)

	# Snapshot dos 3 ativos
	snapshots = []
	for sym in WATCHLIST:
		d = get_tradingview_analysis(sym, Interval.INTERVAL_1_DAY)
		if d:
			tag = "🟢" if "BUY" in d["rec"] else "🔴" if "SELL" in d["rec"] else "⚪"
			snapshots.append(
				f"   {tag} <b>{sym.replace('USDT','')}/ USDT</b>  "
				f"<code>${d['price']:,.2f}</code>  RSI: {d['rsi']:.0f}  → <i>{d['rec']}</i>"
			)
		time.sleep(0.5)

	snap_txt = "\n".join(snapshots) if snapshots else "   Indisponível no momento."
	now_str  = datetime.now(timezone.utc).strftime("%d/%m/%Y")

	mensagem = (
		f"📊 <b>RESUMO DIÁRIO DO MERCADO</b> — {now_str}\n"
		f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n"
		f"{dom_txt}"
		f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n"
		f"📡 <b>SNAPSHOT DOS ATIVOS (1D)</b>\n"
		f"{snap_txt}\n"
		f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n"
		f"🛡️ <i>Gerencie o risco. Preserve o capital. O mercado sempre voltará.</i>\n\n"
		f"{random.choice(SABEDORIA)}"
	)
	try:
		bot.send_message(CHAT_ID, mensagem)
	except Exception as e:
		print(f"Erro resumo diário: {e}")

# ╔══════════════════════════════════════════════════════════════╗
# ║                 MENSAGEM DE INICIALIZAÇÃO                   ║
# ╚══════════════════════════════════════════════════════════════╝

def send_startup_message():
	assets_txt = " • ".join([s.replace("USDT", "/USDT") for s in WATCHLIST])
	mensagem = (
		"🟢 <b>SISTEMA INSTITUCIONAL ELITE — ONLINE</b> 🟢\n"
		f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n"
		f"⚙️ Conexão com servidores: <b>✅ ESTABELECIDA</b>\n"
		f"📊 Módulos TradingView (15m/1h/4h/1D): <b>✅ ATIVOS</b>\n"
		f"🧠 Algoritmo Multi-TF + Score Elite: <b>✅ PRONTO</b>\n"
		f"📈 Gráfico Premium (OHLCV + EMA + BB): <b>✅ OK</b>\n"
		f"🧱 Suporte/Resistência (Pivot Points): <b>✅ ATIVO</b>\n"
		f"🌐 Dominância BTC (CoinGecko): <b>✅ MONITORANDO</b>\n"
		f"🛡️ Gestão de Risco ATR-Based: <b>✅ CALIBRADA</b>\n"
		f"🌍 Radar de Notícias Multi-Feed: <b>✅ MONITORANDO</b>\n"
		f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n"
		f"💠 <b>Ativos monitorados:</b>\n   {assets_txt}\n"
		f"⏱️ <b>Varredura de sinais:</b> a cada 30 minutos\n"
		f"📰 <b>Notícias:</b> a cada 2 horas\n"
		f"📊 <b>Resumo diário:</b> às 08:00 UTC\n"
		f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n"
		f"<i>Score mínimo para sinal: 5/10\n"
		f"Sinais emitidos apenas quando há confirmação em múltiplos timeframes.</i> 🥂\n\n"
		f"{random.choice(SABEDORIA)}"
	)
	try:
		bot.send_message(CHAT_ID, mensagem)
	except Exception as e:
		print(f"Erro ao enviar startup: {e}")

# ╔══════════════════════════════════════════════════════════════╗
# ║                       SCHEDULER                             ║
# ╚══════════════════════════════════════════════════════════════╝

def scheduler_loop():
	schedule.every(30).minutes.do(scan_all_assets)
	schedule.every(2).hours.do(send_crypto_news)
	schedule.every().day.at("08:00").do(send_daily_summary)

	while True:
		schedule.run_pending()
		time.sleep(1)

# ╔══════════════════════════════════════════════════════════════╗
# ║                    WEBHOOK (Flask)                          ║
# ╚══════════════════════════════════════════════════════════════╝

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
	json_str = request.get_data(as_text=True)
	update   = telebot.types.Update.de_json(json_str)
	bot.process_new_updates([update])
	return "OK", 200

@app.route("/")
def index():
	return "Bot Institucional Elite — Online ✅", 200

# ╔══════════════════════════════════════════════════════════════╗
# ║                         MAIN                                ║
# ╚══════════════════════════════════════════════════════════════╝

if __name__ == "__main__":
	print("🚀 Iniciando Bot Institucional Elite…")

	bot.remove_webhook()
	time.sleep(2)

	if WEBHOOK_URL:
		webhook_full = f"{WEBHOOK_URL}/{TOKEN}"
		bot.set_webhook(url=webhook_full)
		print(f"✅ Webhook definido: {webhook_full}")
	else:
		print("⚠️  RAILWAY_STATIC_URL não definida. Rodando em polling (somente local).")

	send_startup_message()
	threading.Thread(target=scheduler_loop, daemon=True).start()

	if WEBHOOK_URL:
		port = int(os.environ.get("PORT", 8080))
		app.run(host="0.0.0.0", port=port)
	else:
		while True:
			try:
				bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
			except Exception as e:
				print(f"Erro de polling: {e}. Reiniciando em 15s…")
				time.sleep(15)
