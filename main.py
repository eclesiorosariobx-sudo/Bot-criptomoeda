import telebot
import ccxt
import pandas as pd
import mplfinance as mpf
from tradingview_ta import TA_Handler, Interval
import feedparser
import schedule
import time
import threading
import random
import os
from flask import Flask, request

# ─────────────────────────────────────────

TOKEN   = "7734730548:AAHM8SufT9OuA0KoYRGglf24Vm8kQTCrpbA"
CHAT_ID = "-1003780528406"

# Coloque a URL do seu app no Railway aqui:

WEBHOOK_URL = os.environ.get("RAILWAY_STATIC_URL", "").rstrip("/")

# ─────────────────────────────────────────

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ══════════════════════════════════════════

# FRASES DO ESPECIALISTA (100 anos de exp)

# ══════════════════════════════════════════

SABEDORIA = [
"📜 <i>\"Vi o crash de 1929, a bolha das dot-com e o colapso de 2008. O mercado sempre pune a ganância e recompensa a paciência.\"</i>",
"📜 <i>\"Em décadas de operação, aprendi que o stop loss não é fraqueza — é sobrevivência.\"</i>",
"📜 <i>\"O mercado não é inimigo. É um espelho da psicologia humana. Domine a si mesmo e dominará o mercado.\"</i>",
"📜 <i>\"Nunca vi um trader consistente que operava por emoção. A frieza é o seu maior ativo.\"</i>",
"📜 <i>\"Mais importante que o ponto de entrada é saber exatamente onde você está errado antes de entrar.\"</i>",
"📜 <i>\"A maior lição que aprendi: preserve o capital. Quem sobrevive, eventualmente prospera.\"</i>",
"📜 <i>\"Ciclos se repetem porque a natureza humana não muda. Estude a história e terá vantagem sobre 95% do mercado.\"</i>",
]

MOTIVACOES = [
"💎 <b>O mercado transfere dinheiro dos impacientes para os pacientes.</b>",
"🚀 <b>Traders amadores focam nos lucros. Profissionais focam em proteger o capital.</b>",
"🦅 <b>A disciplina é a ponte entre a meta e a realização.</b>",
"🔥 <b>Um dia ruim de trade não define sua carreira.</b>",
"👑 <b>O sucesso no mercado financeiro é 20% estratégia e 80% psicologia.</b>",
]

# ══════════════════════════════════════════

# ANÁLISE TRADINGVIEW

# ══════════════════════════════════════════

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
		price      = analysis.indicators["close"]
		rsi        = analysis.indicators.get("RSI", 0)
		macd       = analysis.indicators.get("MACD.macd", 0)
		macd_sig   = analysis.indicators.get("MACD.signal", 0)
		bb_upper   = analysis.indicators.get("BB.upper", 0)
		bb_lower   = analysis.indicators.get("BB.lower", 0)
		volume     = analysis.indicators.get("volume", 0)
		ema_9      = analysis.indicators.get("EMA9",  price)
		ema_21     = analysis.indicators.get("EMA21", price)
		return {
			"rec": rec, "price": price, "rsi": rsi,
			"macd": macd, "macd_sig": macd_sig,
			"bb_upper": bb_upper, "bb_lower": bb_lower,
			"volume": volume, "ema_9": ema_9, "ema_21": ema_21,
		}
	except Exception as e:
		print(f"Erro TV: {e}")
		return None

def get_multi_timeframe(symbol="BTCUSDT"):
	"""Confirma o sinal em 3 timeframes para maior precisão."""
	tf_map = {
		"15min": Interval.INTERVAL_15_MINUTES,
		"1h":    Interval.INTERVAL_1_HOUR,
		"4h":    Interval.INTERVAL_4_HOURS,
	}
	results = {}
	for label, interval in tf_map.items():
		data = get_tradingview_analysis(symbol, interval)
		if data:
			results[label] = data
	return results

def score_signal(tf_data):
	"""
	Pontua a qualidade do sinal de 0 a 10.
	Retorna (score, direction) onde direction é 'BUY' ou 'SELL'.
	"""
	buy_score  = 0
	sell_score = 0

	for label, d in tf_data.items():
		weight = {"15min": 1, "1h": 2, "4h": 3}.get(label, 1)
		rec = d["rec"]
		if "STRONG_BUY" in rec:
			buy_score += 2 * weight
		elif "BUY" in rec:
			buy_score += 1 * weight
		elif "STRONG_SELL" in rec:
			sell_score += 2 * weight
		elif "SELL" in rec:
			sell_score += 1 * weight

	max_score = 18  # (2+4+6) * 1.5 normalizado
	if buy_score > sell_score and buy_score >= 4:
		return round((buy_score / max_score) * 10, 1), "BUY"
	elif sell_score > buy_score and sell_score >= 4:
		return round((sell_score / max_score) * 10, 1), "SELL"
	return 0, "NEUTRAL"

# ══════════════════════════════════════════

# GRÁFICO PREMIUM

# ══════════════════════════════════════════

def generate_premium_chart(symbol="BTC/USDT", timeframe="1h", limit=120):
	try:
		exchange = ccxt.binance()
		bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
		df = pd.DataFrame(bars, columns=["time","open","high","low","close","volume"])
		df["time"] = pd.to_datetime(df["time"], unit="ms")
		df.set_index("time", inplace=True)

		mc = mpf.make_marketcolors(up="#089981", down="#F23645", inherit=True)
		s  = mpf.make_mpf_style(
			marketcolors=mc,
			gridstyle="dotted",
			y_on_right=True,
			facecolor="#131722",
			edgecolor="#363c4e",
			figcolor="#131722",
			rc={
				"text.color":       "#D1D4DC",
				"axes.labelcolor":  "#D1D4DC",
				"xtick.color":      "#D1D4DC",
				"ytick.color":      "#D1D4DC",
			},
		)

		filename = "premium_chart.png"
		mpf.plot(
			df, type="candle", volume=True, mav=(9, 21, 50),
			style=s,
			title=f"\n{symbol} — Análise Algorítmica Institucional ({timeframe})",
			savefig=filename,
			figsize=(14, 7),
		)
		return filename
	except Exception as e:
		print(f"Erro ao gerar gráfico: {e}")
		return None

# ══════════════════════════════════════════

# ENVIO DE SINAL

# ══════════════════════════════════════════

def send_trade_signal():
	tf_data = get_multi_timeframe("BTCUSDT")
	if not tf_data:
		return

	score, direction = score_signal(tf_data)
	if direction == "NEUTRAL" or score < 4:
		print(f"Sem sinal relevante (score={score}, dir={direction})")
		return

	# Usa dados do 1h como referência principal
	d1h = tf_data.get("1h", list(tf_data.values())[0])
	price    = d1h["price"]
	rsi      = d1h["rsi"]
	macd     = d1h["macd"]
	macd_sig = d1h["macd_sig"]
	volume   = d1h["volume"]
	rec_15   = tf_data.get("15min", {}).get("rec", "—")
	rec_1h   = tf_data.get("1h",   {}).get("rec", "—")
	rec_4h   = tf_data.get("4h",   {}).get("rec", "—")

	is_buy = direction == "BUY"
	trade_type = "🟢 COMPRA (LONG)" if is_buy else "🔴 VENDA (SHORT)"
	emoji = "📈" if is_buy else "📉"

	# Níveis de TP escalonados + SL
	if is_buy:
		tp1 = price * 1.015
		tp2 = price * 1.030
		tp3 = price * 1.050
		sl  = price * 0.985
	else:
		tp1 = price * 0.985
		tp2 = price * 0.970
		tp3 = price * 0.950
		sl  = price * 1.015

	# Qualidade do sinal
	stars = "⭐" * min(int(score), 5) + ("✨" if score >= 8 else "")
	quality = "EXCEPCIONAL" if score >= 8 else "ALTA" if score >= 6 else "MODERADA"

	rsi_alerta = ""
	if rsi > 70:
		rsi_alerta = "\n⚠️ <i>RSI sobrecomprado — reduza o tamanho da posição.</i>"
	elif rsi < 30:
		rsi_alerta = "\n⚠️ <i>RSI sobrevendido — confirmação de reversão.</i>"

	macd_status = "Alta ↑" if macd > macd_sig else "Baixa ↓"

	mensagem = (
		f"{emoji} <b>SINAL INSTITUCIONAL DETECTADO</b> {emoji}\n"
		f"<i>Análise Algorítmica Multi-Timeframe • 100 anos de experiência</i>\n"
		f"{'─'*32}\n"
		f"💎 <b>Ativo:</b> #BTC/USDT\n"
		f"🎯 <b>Operação:</b> {trade_type}\n"
		f"📊 <b>Qualidade do Sinal:</b> {stars} ({quality})\n"
		f"🔢 <b>Score:</b> {score}/10\n"
		f"{'─'*32}\n"
		f"💰 <b>Entrada (Mercado):</b> <code>${price:,.2f}</code>\n"
		f"✅ <b>Take Profit 1 (33%):</b> <code>${tp1:,.2f}</code>\n"
		f"✅ <b>Take Profit 2 (33%):</b> <code>${tp2:,.2f}</code>\n"
		f"✅ <b>Take Profit 3 (34%):</b> <code>${tp3:,.2f}</code>\n"
		f"❌ <b>Stop Loss:</b> <code>${sl:,.2f}</code>\n"
		f"{'─'*32}\n"
		f"📡 <b>Confirmação Multi-Timeframe:</b>\n"
		f"   • 15min → <i>{rec_15}</i>\n"
		f"   •   1h  → <i>{rec_1h}</i>\n"
		f"   •   4h  → <i>{rec_4h}</i>\n"
		f"{'─'*32}\n"
		f"📉 <b>RSI (1H):</b> {rsi:.1f}{rsi_alerta}\n"
		f"⚡ <b>MACD:</b> {macd_status}\n"
		f"{'─'*32}\n"
		f"⚠️ <i>Utilize no máximo 1% a 2% da banca. Escalone nos TPs.\n"
		f"Nunca opere sem stop loss definido.</i>\n"
		f"\n{random.choice(SABEDORIA)}"
	)

	chart_file = generate_premium_chart()

	try:
		if chart_file and os.path.exists(chart_file):
			with open(chart_file, "rb") as photo:
				bot.send_photo(CHAT_ID, photo, caption=mensagem)
			os.remove(chart_file)
		else:
			bot.send_message(CHAT_ID, mensagem)
	except Exception as e:
		print(f"Erro ao enviar sinal: {e}")

# ══════════════════════════════════════════

# NOTÍCIAS

# ══════════════════════════════════════════

def send_crypto_news():
	try:
		feed = feedparser.parse("https://cointelegraph.com.br/rss")
		if feed.entries:
			entry = feed.entries[0]
			mensagem = (
				"🌍 <b>RADAR DO MERCADO</b> 🌍\n"
				f"📰 <b>{entry.title}</b>\n"
				f"<i>{entry.summary[:200]}…</i>\n"
				f"🔗 <a href=\"{entry.link}\">Ler matéria completa</a>\n\n"
				f"💡 {random.choice(MOTIVACOES)}\n\n"
				f"{random.choice(SABEDORIA)}"
			)
			bot.send_message(CHAT_ID, mensagem, disable_web_page_preview=False)
	except Exception as e:
		print(f"Erro ao buscar notícias: {e}")

# ══════════════════════════════════════════

# MENSAGEM DE INICIALIZAÇÃO

# ══════════════════════════════════════════

def send_startup_message():
	mensagem = (
		"🟢 <b>SISTEMA INSTITUCIONAL DE TRADING ONLINE</b> 🟢\n"
		"⚙️ Conexão estabelecida com os servidores…\n"
		"📊 Módulos TradingView (15min / 1h / 4h): <b>[ ATIVOS ]</b>\n"
		"🧠 Algoritmo Multi-Timeframe + Score: <b>[ PRONTO ]</b>\n"
		"📈 Geração de gráficos premium: <b>[ OK ]</b>\n"
		"🌍 Radar de notícias: <b>[ MONITORANDO ]</b>\n"
		"─────────────────────────────────\n"
		"<i>A partir de agora o mercado será monitorado 24h.\n"
		"Sinais enviados somente quando o score justifica a operação.</i> 🥂\n\n"
		f"{random.choice(SABEDORIA)}"
	)
	try:
		bot.send_message(CHAT_ID, mensagem)
	except Exception as e:
		print(f"Erro ao enviar startup: {e}")

# ══════════════════════════════════════════

# SCHEDULER

# ══════════════════════════════════════════

def scheduler_loop():
	schedule.every(30).minutes.do(send_trade_signal)
	schedule.every(2).hours.do(send_crypto_news)

	while True:
		schedule.run_pending()
		time.sleep(1)

# ══════════════════════════════════════════

# WEBHOOK (Flask) — estável no Railway

# ══════════════════════════════════════════

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
	json_str = request.get_data(as_text=True)
	update   = telebot.types.Update.de_json(json_str)
	bot.process_new_updates([update])
	return "OK", 200

@app.route("/")
def index():
	return "Bot de Trading Institucional — Online ✅", 200

# ══════════════════════════════════════════

# MAIN

# ══════════════════════════════════════════

if __name__ == "__main__":
	print("Iniciando Bot Institucional…")

	# Remove qualquer webhook ou polling anterior
	bot.remove_webhook()
	time.sleep(2)

	if WEBHOOK_URL:
		webhook_full = f"{WEBHOOK_URL}/{TOKEN}"
		bot.set_webhook(url=webhook_full)
		print(f"Webhook definido: {webhook_full}")
	else:
		print("⚠️  RAILWAY_STATIC_URL não definida. Rodando em polling (somente local).")

	send_startup_message()

	# Inicia o agendador em thread separada
	threading.Thread(target=scheduler_loop, daemon=True).start()

	if WEBHOOK_URL:
		port = int(os.environ.get("PORT", 8080))
		app.run(host="0.0.0.0", port=port)
	else:
		# Fallback para testes locais
		while True:
			try:
				bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
			except Exception as e:
				print(f"Erro de polling: {e}. Reiniciando em 15s...")
				time.sleep(15)
