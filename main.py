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
import re
import html
from datetime import datetime, timezone
from flask import Flask, request

# ╔══════════════════════════════════════════════════════════════╗
# ║    INSTITUTIONAL BITCOIN-ONLY TRADING SYSTEM — ELITE        ║
# ╚══════════════════════════════════════════════════════════════╝

TOKEN    = "7734730548:AAHM8SufT9OuA0KoYRGglf24Vm8kQTCrpbA"
CHAT_ID  = "-1003780528406"
WEBHOOK_URL = os.environ.get("RAILWAY_STATIC_URL", "").rstrip("/")

# WATCHLIST: Bitcoin pairs only
WATCHLIST = ["BTCUSDT", "BTCUSDC"]  # Binance pairs
WATCHLIST_EUR = ["BTC/EUR"]  # Kraken pair

PAIR_CONFIGS = {
    "BTCUSDT": {"exchange": "binance", "symbol": "BTC/USDT", "currency": "USD"},
    "BTCUSDC": {"exchange": "binance", "symbol": "BTC/USDC", "currency": "USD"},
    "BTC/EUR": {"exchange": "kraken", "symbol": "BTC/EUR", "currency": "EUR"},
}

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ╔══════════════════════════════════════════════════════════════╗
# ║          EXECUTIVE WISDOM — INSTITUTIONAL INSIGHTS          ║
# ╚══════════════════════════════════════════════════════════════╝

EXECUTIVE_INSIGHTS = [
    "📊 Preservação de capital precede geração de lucro.",
    "🛑 Stop loss define sobrevivência. Profissionais sabem.",
    "⚡ Eficiência de mercado transfere riqueza de reativos para sistemáticos.",
    "🧠 Disciplina emocional separa institucionais de especuladores.",
    "📈 Tendência + precisão técnica vence previsões.",
    "🔐 Gestão de risco é a única vantagem que compõe.",
    "💹 Análise de volatilidade revela ciclos institucionais.",
    "📋 Volume autentica cada descoberta de preço.",
    "⚙️ Disciplina de execução vence timing de mercado.",
]

# ╔══════════════════════════════════════════════════════════════╗
# ║           MULTI-TIMEFRAME TRADINGVIEW ANALYSIS              ║
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
        rec = analysis.summary["RECOMMENDATION"]
        buy_count = analysis.summary.get("BUY", 0)
        sell_count = analysis.summary.get("SELL", 0)
        neutral = analysis.summary.get("NEUTRAL", 0)
        price = analysis.indicators["close"]
        rsi = analysis.indicators.get("RSI", 0)
        rsi14 = analysis.indicators.get("RSI[1]", rsi)
        macd = analysis.indicators.get("MACD.macd", 0)
        macd_sig = analysis.indicators.get("MACD.signal", 0)
        macd_hist = macd - macd_sig
        bb_upper = analysis.indicators.get("BB.upper", 0)
        bb_lower = analysis.indicators.get("BB.lower", 0)
        bb_mid = (bb_upper + bb_lower) / 2 if bb_upper and bb_lower else price
        volume = analysis.indicators.get("volume", 0)
        ema9 = analysis.indicators.get("EMA9", price)
        ema21 = analysis.indicators.get("EMA21", price)
        ema50 = analysis.indicators.get("EMA50", price)
        ema200 = analysis.indicators.get("EMA200", price)
        adx = analysis.indicators.get("ADX", 0)
        stoch_k = analysis.indicators.get("Stoch.K", 50)
        stoch_d = analysis.indicators.get("Stoch.D", 50)
        atr = analysis.indicators.get("ATR", 0)
        
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
    timeframe_map = {
        "15min": Interval.INTERVAL_15_MINUTES,
        "1h": Interval.INTERVAL_1_HOUR,
        "4h": Interval.INTERVAL_4_HOURS,
        "1d": Interval.INTERVAL_1_DAY,
    }
    results = {}
    for label, interval in timeframe_map.items():
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
        
        rsi = d.get("rsi", 50)
        if rsi < 35:
            buy_score += 1 * w
        elif rsi > 65:
            sell_score += 1 * w
        
        if d.get("macd_hist", 0) > 0:
            buy_score += 0.5 * w
        elif d.get("macd_hist", 0) < 0:
            sell_score += 0.5 * w
    
    max_score = 30
    if buy_score > sell_score and buy_score >= 5:
        return min(round((buy_score / max_score) * 10, 1), 10.0), "COMPRA"
    elif sell_score > buy_score and sell_score >= 5:
        return min(round((sell_score / max_score) * 10, 1), 10.0), "VENDA"
    
    return 0, "NEUTRO"

# ╔══════════════════════════════════════════════════════════════╗
# ║         SUPPORT & RESISTANCE — PIVOT POINT ANALYSIS         ║
# ╚══════════════════════════════════════════════════════════════╝

def calculate_support_resistance(symbol="BTC/USDT", timeframe="1d", limit=30, exchange_name="binance"):
    try:
        if exchange_name == "kraken":
            exchange = ccxt.kraken()
        else:
            exchange = ccxt.binance()
        
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=["time", "open", "high", "low", "close", "volume"])
        
        last = df.iloc[-2]
        H, L, C = last["high"], last["low"], last["close"]
        P = (H + L + C) / 3
        R1 = 2 * P - L
        R2 = P + (H - L)
        R3 = H + 2 * (P - L)
        S1 = 2 * P - H
        S2 = P - (H - L)
        S3 = L - 2 * (H - P)
        
        recent_high = df["high"].max()
        recent_low = df["low"].min()
        
        return {
            "pivot": P, "r1": R1, "r2": R2, "r3": R3,
            "s1": S1, "s2": S2, "s3": S3,
            "recent_high": recent_high, "recent_low": recent_low,
        }
    except Exception as e:
        print(f"Erro S/R: {e}")
        return None

# ╔══════════════════════════════════════════════════════════════╗
# ║               BITCOIN DOMINANCE MONITORING                  ║
# ╚══════════════════════════════════════════════════════════════╝

def get_bitcoin_dominance():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(url, headers=headers, timeout=8)
        data = r.json()
        
        if "data" not in data:
            return None
        
        dominance = data["data"]["market_cap_percentage"]["btc"]
        total_mcap = data["data"]["total_market_cap"]["usd"]
        eth_dom = data["data"]["market_cap_percentage"].get("eth", 0)
        
        return {
            "dominance": round(dominance, 2),
            "total_mcap": total_mcap,
            "eth_dom": round(eth_dom, 2),
        }
    except Exception as e:
        print(f"Erro dominância: {e}")
        return None

# ╔══════════════════════════════════════════════════════���═══════╗
# ║           GET 24H PRICE CHANGE & VOLATILITY DATA            ║
# ╚══════════════════════════════════════════════════════════════╝

def get_24h_metrics(symbol="BTC/USDT", exchange_name="binance"):
    """Fetch 24h price change and volatility metrics."""
    try:
        if exchange_name == "kraken":
            exchange = ccxt.kraken()
        else:
            exchange = ccxt.binance()
        
        bars_24h = exchange.fetch_ohlcv(symbol, timeframe="1d", limit=2)
        
        if len(bars_24h) < 2:
            return None
        
        prev_close = bars_24h[0][4]
        current_price = bars_24h[1][4]
        high_24h = bars_24h[1][2]
        low_24h = bars_24h[1][3]
        
        price_change_24h = ((current_price - prev_close) / prev_close) * 100
        volatility = ((high_24h - low_24h) / current_price) * 100
        
        return {
            "change_24h": round(price_change_24h, 2),
            "high_24h": high_24h,
            "low_24h": low_24h,
            "volatility": round(volatility, 2),
        }
    except Exception as e:
        print(f"Erro métricas 24h: {e}")
        return None

# ╔══════════════════════════════════════════════════════════════╗
# ║            ADVANCED RISK MANAGEMENT — ATR-BASED             ║
# ╚══════════════════════════════════════════════════════════════╝

def calculate_risk_management(price, direction, atr, score):
    """Calcula entrada, TPs e SL baseado em ATR."""
    if not atr or atr == 0:
        atr = price * 0.015
    
    atr_mult_sl = 1.5
    atr_mult_tp1 = 1.5
    atr_mult_tp2 = 3.0
    atr_mult_tp3 = 5.0
    
    if direction == "COMPRA":
        sl = price - (atr * atr_mult_sl)
        tp1 = price + (atr * atr_mult_tp1)
        tp2 = price + (atr * atr_mult_tp2)
        tp3 = price + (atr * atr_mult_tp3)
    else:
        sl = price + (atr * atr_mult_sl)
        tp1 = price - (atr * atr_mult_tp1)
        tp2 = price - (atr * atr_mult_tp2)
        tp3 = price - (atr * atr_mult_tp3)
    
    sl_dist = abs(price - sl)
    rr1 = round(abs(tp1 - price) / sl_dist, 2) if sl_dist else 0
    rr2 = round(abs(tp2 - price) / sl_dist, 2) if sl_dist else 0
    rr3 = round(abs(tp3 - price) / sl_dist, 2) if sl_dist else 0
    
    example_capital = 1000
    risk_per_trade = example_capital * 0.01
    position_size = round(risk_per_trade / sl_dist, 6) if sl_dist else 0
    
    return {
        "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3,
        "rr1": rr1, "rr2": rr2, "rr3": rr3,
        "atr": atr, "sl_dist": sl_dist,
        "position_size_example": position_size,
    }

# ╔══════════════════════════════════════════════════════════════╗
# ║              ELITE INSTITUTIONAL CHART GENERATION            ║
# ╚══════════════════════════════════════════════════════════════╝

def generate_elite_chart(symbol="BTC/USDT", timeframe="1h", limit=150, levels=None, exchange_name="binance"):
    try:
        if exchange_name == "kraken":
            exchange = ccxt.kraken()
        else:
            exchange = ccxt.binance()
        
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=["time", "open", "high", "low", "close", "volume"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df.set_index("time", inplace=True)
        
        # ── Color Scheme ───────────────────────────────────────
        BG = "#0B0E1A"
        PANEL = "#10142A"
        GREEN = "#00E5A0"
        RED = "#FF3D6B"
        GOLD = "#F5C842"
        BLUE = "#4DA6FF"
        PURPLE = "#B06EFF"
        TEXT = "#CDD6F4"
        GRID = "#1E2440"
        WHITE = "#FFFFFF"
        
        fig = plt.figure(figsize=(18, 11), facecolor=BG)
        gs = GridSpec(4, 1, figure=fig, hspace=0.04, height_ratios=[3.5, 0.8, 0.8, 0.9])
        
        ax_candle = fig.add_subplot(gs[0])
        ax_vol = fig.add_subplot(gs[1], sharex=ax_candle)
        ax_rsi = fig.add_subplot(gs[2], sharex=ax_candle)
        ax_macd = fig.add_subplot(gs[3], sharex=ax_candle)
        
        for ax in [ax_candle, ax_vol, ax_rsi, ax_macd]:
            ax.set_facecolor(PANEL)
            ax.tick_params(colors=TEXT, labelsize=8)
            ax.spines[:].set_color(GRID)
            ax.yaxis.label.set_color(TEXT)
        
        # ── Candles ────────────────────────────────────────────
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        xs = np.arange(len(df))
        
        for i, (o, h, l, c) in enumerate(zip(opens, highs, lows, closes)):
            color = GREEN if c >= o else RED
            ax_candle.plot([i, i], [l, h], color=color, linewidth=0.8, alpha=0.9)
            ax_candle.bar(i, abs(c - o), bottom=min(o, c), color=color, width=0.7, alpha=0.95)
        
        # ── EMAs ───────────────────────────────────────────────
        close_s = df["close"]
        ema9 = close_s.ewm(span=9, adjust=False).mean()
        ema21 = close_s.ewm(span=21, adjust=False).mean()
        ema50 = close_s.ewm(span=50, adjust=False).mean()
        ema200 = close_s.ewm(span=200, adjust=False).mean()
        
        ax_candle.plot(xs, ema9.values, color=GOLD, linewidth=1.1, label="EMA9", alpha=0.85)
        ax_candle.plot(xs, ema21.values, color=BLUE, linewidth=1.1, label="EMA21", alpha=0.85)
        ax_candle.plot(xs, ema50.values, color=PURPLE, linewidth=1.1, label="EMA50", alpha=0.85)
        ax_candle.plot(xs, ema200.values, color=RED, linewidth=1.3, label="EMA200", alpha=0.75, linestyle="--")
        
        # ── Bollinger Bands ────────────────────────────────────
        bb_mid = close_s.rolling(20).mean()
        bb_std = close_s.rolling(20).std()
        bb_up = bb_mid + 2 * bb_std
        bb_dn = bb_mid - 2 * bb_std
        
        ax_candle.fill_between(xs, bb_up.values, bb_dn.values, alpha=0.06, color=BLUE)
        ax_candle.plot(xs, bb_up.values, color=BLUE, linewidth=0.5, alpha=0.4, linestyle=":")
        ax_candle.plot(xs, bb_dn.values, color=BLUE, linewidth=0.5, alpha=0.4, linestyle=":")
        
        # ── Support/Resistance Levels ──────────────────────────
        if levels:
            for key, val, color, lbl in [
                ("r2", levels.get("r2"), "#FF6B6B", "R2"),
                ("r1", levels.get("r1"), "#FFA07A", "R1"),
                ("pivot", levels.get("pivot"), GOLD, "P"),
                ("s1", levels.get("s1"), "#90EE90", "S1"),
                ("s2", levels.get("s2"), "#32CD32", "S2"),
            ]:
                if val:
                    ax_candle.axhline(val, color=color, linewidth=0.8, linestyle="--", alpha=0.6)
                    ax_candle.text(len(xs) - 1, val, f" {lbl}", color=color, fontsize=7, va="center", fontweight="bold")
        
        # ── Legend & Title ─────────────────────────────────────
        legend = ax_candle.legend(loc="upper left", fontsize=7.5, facecolor="#0B0E1A", edgecolor=GRID, labelcolor=TEXT, framealpha=0.9)
        
        now_str = datetime.now(timezone.utc).strftime("%d/%m %H:%M UTC")
        ax_candle.set_title(
            f"{symbol} | {timeframe.upper()} | {now_str}",
            color=WHITE, fontsize=10, fontweight="bold", loc="left", pad=10, fontfamily="monospace"
        )
        
        price_label = "Preço (USD)" if "USD" in symbol else "Preço (EUR)"
        ax_candle.set_ylabel(price_label, color=TEXT, fontsize=8)
        ax_candle.yaxis.set_label_position("right")
        ax_candle.yaxis.tick_right()
        ax_candle.grid(axis="y", color=GRID, linewidth=0.5, alpha=0.6)
        plt.setp(ax_candle.get_xticklabels(), visible=False)
        
        # ── Volume ─────────────────────────────────────────────
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
        
        # ── RSI ────────────────────────────────────────────────
        delta = close_s.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        ax_rsi.plot(xs, rsi.values, color=PURPLE, linewidth=1.2)
        ax_rsi.axhline(70, color=RED, linewidth=0.6, linestyle="--", alpha=0.5)
        ax_rsi.axhline(30, color=GREEN, linewidth=0.6, linestyle="--", alpha=0.5)
        ax_rsi.axhline(50, color=GRID, linewidth=0.4, linestyle=":", alpha=0.4)
        ax_rsi.fill_between(xs, rsi.values, 70, where=(rsi.values >= 70), color=RED, alpha=0.15)
        ax_rsi.fill_between(xs, rsi.values, 30, where=(rsi.values <= 30), color=GREEN, alpha=0.15)
        ax_rsi.set_ylim(0, 100)
        ax_rsi.set_ylabel("RSI", color=TEXT, fontsize=7)
        ax_rsi.yaxis.set_label_position("right")
        ax_rsi.yaxis.tick_right()
        ax_rsi.set_yticks([30, 50, 70])
        ax_rsi.grid(axis="y", color=GRID, linewidth=0.4, alpha=0.5)
        plt.setp(ax_rsi.get_xticklabels(), visible=False)
        
        # ── MACD ───────────────────────────────────────────────
        ema12 = close_s.ewm(span=12, adjust=False).mean()
        ema26 = close_s.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal = macd_line.ewm(span=9, adjust=False).mean()
        hist = macd_line - signal
        
        hist_colors = [GREEN if v >= 0 else RED for v in hist.values]
        ax_macd.bar(xs, hist.values, color=hist_colors, alpha=0.7, width=0.7)
        ax_macd.plot(xs, macd_line.values, color=BLUE, linewidth=1.0, label="MACD")
        ax_macd.plot(xs, signal.values, color=GOLD, linewidth=1.0, label="Signal")
        ax_macd.axhline(0, color=GRID, linewidth=0.5, alpha=0.6)
        ax_macd.set_ylabel("MACD", color=TEXT, fontsize=7)
        ax_macd.yaxis.set_label_position("right")
        ax_macd.yaxis.tick_right()
        ax_macd.grid(axis="y", color=GRID, linewidth=0.4, alpha=0.5)
        
        # ── X-Axis dates ───────────────────────────────────────
        step = max(1, len(xs) // 10)
        tick_pos = xs[::step]
        tick_lbl = [df.index[i].strftime("%d/%m %Hh") for i in tick_pos]
        ax_macd.set_xticks(tick_pos)
        ax_macd.set_xticklabels(tick_lbl, fontsize=7, color=TEXT)
        
        # ── Top Golden Border ──────────────────────────────────
        fig.patches.append(
            mpatches.FancyBboxPatch(
                (0, 0.995), 1, 0.005,
                transform=fig.transFigure, clip_on=False,
                boxstyle="square,pad=0", facecolor=GOLD, edgecolor="none"
            )
        )
        
        filename = f"elite_chart_{symbol.replace('/', '')}.png"
        plt.savefig(filename, dpi=150, bbox_inches="tight", facecolor=BG, edgecolor="none")
        plt.close(fig)
        
        return filename
    except Exception as e:
        print(f"Erro ao gerar gráfico: {e}")
        return None

# ╔══════════════════════════════════════════════════════════════╗
# ║                   SIGNAL FORMATTING HELPERS                 ║
# ╚══════════════��═══════════════════════════════════════════════╝

def format_price(price, currency="USD"):
    if currency == "EUR":
        return f"€{price:,.2f}"
    else:
        return f"${price:,.2f}"

def recommendation_to_text(rec):
    if "STRONG_BUY" in rec:
        return "FORTE_COMPRA"
    elif "BUY" in rec:
        return "COMPRA"
    elif "STRONG_SELL" in rec:
        return "FORTE_VENDA"
    elif "SELL" in rec:
        return "VENDA"
    else:
        return "NEUTRO"

def get_signal_strength_label(score):
    if score >= 8.5:
        return "EXCEPCIONAL ⭐"
    elif score >= 7.0:
        return "FORTE 💪"
    elif score >= 5.5:
        return "MODERADO ⚠️"
    else:
        return "FRACO 📍"

def get_rsi_context(rsi):
    if rsi > 72:
        return f"🔴 SOBRECOMPRADO ({rsi:.0f})"
    elif rsi > 65:
        return f"🟠 ESTENDIDO ({rsi:.0f})"
    elif rsi < 28:
        return f"🟢 SOBREVENDIDO ({rsi:.0f})"
    elif rsi < 35:
        return f"🟡 DEPRIMIDO ({rsi:.0f})"
    else:
        return f"🔵 NEUTRO ({rsi:.0f})"

def get_adx_context(adx):
    if adx > 35:
        return "🔥 TENDÊNCIA FORTE"
    elif adx > 25:
        return "⚡ TENDÊNCIA MÉDIA"
    elif adx > 20:
        return "💤 TENDÊNCIA FRACA"
    else:
        return "❓ SEM DIREÇÃO"

def get_macd_context(macd_hist, macd, macd_sig):
    if macd_hist > 0 and macd > macd_sig:
        return "📈 ACELERAÇÃO ALTISTA"
    elif macd_hist < 0 and macd < macd_sig:
        return "📉 ACELERAÇÃO BAIXISTA"
    elif macd_hist > 0:
        return "🟢 DIVERGÊNCIA ALTISTA"
    elif macd_hist < 0:
        return "🔴 DIVERGÊNCIA BAIXISTA"
    else:
        return "↔️ CRUZAMENTO"

# ╔══════════════════════════════════════════════════════════════╗
# ║                 INSTITUTIONAL SIGNAL DELIVERY               ║
# ╚══════════════════════════════════════════════════════════════╝

def send_trade_signal(symbol_key="BTCUSDT"):
    """Envia sinal de trade institucional com formatação profissional."""
    
    config = PAIR_CONFIGS.get(symbol_key)
    if not config:
        return
    
    symbol_display = config["symbol"]
    exchange_name = config["exchange"]
    currency = config["currency"]
    symbol_tv = symbol_key
    
    # Get multi-timeframe analysis
    tf_data = get_multi_timeframe(symbol_tv)
    if not tf_data:
        return
    
    score, direction = score_signal(tf_data)
    if direction == "NEUTRO" or score < 5:
        print(f"[{symbol_key}] Sem sinal relevante (score={score}, dir={direction})")
        return
    
    d1h = tf_data.get("1h", list(tf_data.values())[0])
    price = d1h["price"]
    rsi = d1h["rsi"]
    macd = d1h["macd"]
    macd_sig = d1h["macd_sig"]
    macd_hist = d1h["macd_hist"]
    adx = d1h.get("adx", 0)
    atr = d1h.get("atr", 0)
    
    rec_15 = recommendation_to_text(tf_data.get("15min", {}).get("rec", "NEUTRO"))
    rec_1h = recommendation_to_text(tf_data.get("1h", {}).get("rec", "NEUTRO"))
    rec_4h = recommendation_to_text(tf_data.get("4h", {}).get("rec", "NEUTRO"))
    rec_1d = recommendation_to_text(tf_data.get("1d", {}).get("rec", "NEUTRO"))
    
    # Risk management
    rm = calculate_risk_management(price, direction, atr, score)
    
    # Support/Resistance
    ccxt_symbol = config["symbol"]
    levels = calculate_support_resistance(ccxt_symbol, exchange_name=exchange_name)
    
    # Bitcoin dominance
    dom = get_bitcoin_dominance()
    
    # 24h metrics
    metrics_24h = get_24h_metrics(config["symbol"], exchange_name=exchange_name)
    
    # Determine direction
    direction_icon = "🟢 COMPRA ▲" if direction == "COMPRA" else "🔴 VENDA ▼"
    
    # Timestamp
    now_str = datetime.now(timezone.utc).strftime("%d/%m %H:%M UTC")
    
    # Build compact signal message
    signal_strength = get_signal_strength_label(score)
    price_str = format_price(price, currency)
    tp1_str = format_price(rm['tp1'], currency)
    tp2_str = format_price(rm['tp2'], currency)
    tp3_str = format_price(rm['tp3'], currency)
    sl_str = format_price(rm['sl'], currency)
    
    # COMPACT MESSAGE FORMAT (máximo 700 caracteres)
    message = (
        f"<b>₿ BITCOIN SIGNAL</b>\n"
        f"{'─' * 30}\n"
        f"📊 Par: <code>{symbol_display}</code>\n"
        f"{direction_icon}\n"
        f"⏰ {now_str}\n"
        f"🎯 Score: <code>{score:.1f}/10</code> {signal_strength}\n"
        f"{'─' * 30}\n"
        f"\n<b>📍 ENTRADA</b>\n"
        f"▸ <code>{price_str}</code>\n"
        f"\n<b>🎁 ALVOS (33/33/34%)</b>\n"
        f"▸ TP1: <code>{tp1_str}</code> (R:R {rm['rr1']}x)\n"
        f"▸ TP2: <code>{tp2_str}</code> (R:R {rm['rr2']}x)\n"
        f"▸ TP3: <code>{tp3_str}</code> (R:R {rm['rr3']}x)\n"
        f"▸ SL: <code>{sl_str}</code>\n"
        f"{'─' * 30}\n"
        f"\n<b>📈 MULTI-TF</b>\n"
        f"▸ 15m: {rec_15}\n"
        f"▸ 1h: {rec_1h}\n"
        f"▸ 4h: {rec_4h}\n"
        f"▸ 1d: {rec_1d}\n"
        f"\n<b>📊 TÉCNICOS</b>\n"
        f"▸ {get_rsi_context(rsi)}\n"
        f"▸ {get_adx_context(adx)}\n"
        f"▸ {get_macd_context(macd_hist, macd, macd_sig)}\n"
    )
    
    # Add 24h metrics if available
    if metrics_24h:
        change_icon = "📈" if metrics_24h['change_24h'] >= 0 else "📉"
        message += (
            f"\n<b>24H</b>\n"
            f"▸ {change_icon} {metrics_24h['change_24h']:+.2f}%\n"
            f"▸ H: {format_price(metrics_24h['high_24h'], currency)}\n"
            f"▸ L: {format_price(metrics_24h['low_24h'], currency)}\n"
        )
    
    # Add dominance if available
    if dom:
        message += (
            f"\n<b>👑 DOMINÂNCIA</b>\n"
            f"▸ BTC: {dom['dominance']}%\n"
            f"▸ Cap: ${dom['total_mcap']/1e12:.2f}T\n"
        )
    
    message += (
        f"\n{'─' * 30}\n"
        f"🛡️ Risco: 1-2% da conta\n"
        f"⚑ {random.choice(EXECUTIVE_INSIGHTS)}\n"
    )
    
    # Generate chart
    chart_file = generate_elite_chart(config["symbol"], timeframe="1h", levels=levels, exchange_name=exchange_name)
    
    try:
        if chart_file and os.path.exists(chart_file):
            with open(chart_file, "rb") as photo:
                if len(message) > 1024:
                    bot.send_photo(CHAT_ID, photo)
                    bot.send_message(CHAT_ID, message)
                else:
                    bot.send_photo(CHAT_ID, photo, caption=message)
            os.remove(chart_file)
        else:
            bot.send_message(CHAT_ID, message)
        
        print(f"[{symbol_key}] Sinal enviado — score={score}, dir={direction}")
    except Exception as e:
        print(f"Erro ao enviar sinal [{symbol_key}]: {e}")

def scan_all_bitcoin_pairs():
    """Varre todos os pares BTC e emite sinais."""
    all_pairs = WATCHLIST + WATCHLIST_EUR
    for pair in all_pairs:
        send_trade_signal(pair)
        time.sleep(2)

# ╔══════════════════════════════════════════════════════════════╗
# ║                  ELITE NEWS RADAR                           ║
# ╚══════════════════════════════════════════════════════════════╝

def send_crypto_news():
    """Distribui notícias do mercado cripto."""
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
    
    dom = get_bitcoin_dominance()
    dom_txt = ""
    if dom:
        dom_txt = (
            f"\n👑 BTC: {dom['dominance']}% | Cap: ${dom['total_mcap']/1e12:.2f}T"
        )
    
    entry = random.choice(entries)
    summary_raw = entry.get("summary", "")
    summary_clean = re.sub(r'<[^>]+>', '', summary_raw)
    summary_clean = html.unescape(summary_clean)
    summary = summary_clean.strip()[:200]
    
    message = (
        f"<b>📰 NOTÍCIAS DO MERCADO</b>\n"
        f"{'─' * 30}\n"
        f"{entry.title[:80]}\n\n"
        f"<i>{summary}…</i>\n\n"
        f"🔗 <a href=\"{entry.link}\">Ler completo</a>"
        f"{dom_txt}\n"
        f"{'─' * 30}\n"
        f"⚑ {random.choice(EXECUTIVE_INSIGHTS)}"
    )
    
    try:
        bot.send_message(CHAT_ID, message, disable_web_page_preview=False)
    except Exception as e:
        print(f"Erro ao enviar notícias: {e}")

# ╔══════════════════════════════════════════════════════════════╗
# ║                   DAILY MARKET SUMMARY                      ║
# ╚══════════════════════════════════════════════════════════════╝

def send_daily_summary():
    """Entrega resumo diário do mercado Bitcoin."""
    dom = get_bitcoin_dominance()
    dom_txt = ""
    
    if dom:
        mcap_t = dom["total_mcap"] / 1e12
        dom_txt = (
            f"👑 BTC Dom: {dom['dominance']}%\n"
            f"💼 Market Cap: ${mcap_t:.2f}T\n"
            f"🔷 ETH Dom: {dom['eth_dom']}%\n"
        )
    
    # Snapshot of all Bitcoin pairs
    snapshots = []
    all_pairs = WATCHLIST + WATCHLIST_EUR
    
    for pair in all_pairs:
        config = PAIR_CONFIGS.get(pair)
        if not config:
            continue
        
        d = get_tradingview_analysis(pair, Interval.INTERVAL_1_DAY)
        if d:
            rec_text = recommendation_to_text(d["rec"])
            price_str = format_price(d['price'], config["currency"])
            pair_display = config["symbol"]
            rec_emoji = "🟢" if "COMPRA" in rec_text else "🔴" if "VENDA" in rec_text else "⚪"
            
            snapshots.append(
                f"{rec_emoji} <b>{pair_display}</b> {price_str} RSI:{d['rsi']:.0f}"
            )
        
        time.sleep(0.5)
    
    snap_txt = "\n".join(snapshots) if snapshots else "Dados indisponíveis."
    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    
    message = (
        f"<b>📊 RESUMO DIÁRIO — {now_str}</b>\n"
        f"{'─' * 30}\n"
        f"{dom_txt}"
        f"{'─' * 30}\n"
        f"<b>₿ SNAPSHOT</b>\n"
        f"{snap_txt}\n"
        f"{'─' * 30}\n"
        f"⚑ {random.choice(EXECUTIVE_INSIGHTS)}"
    )
    
    try:
        bot.send_message(CHAT_ID, message)
    except Exception as e:
        print(f"Erro resumo diário: {e}")

# ╔════════════════════════════════════════════════��═════════════╗
# ║                  SYSTEM INITIALIZATION MESSAGE              ║
# ╚══════════════════════════════════════════════════════════════╝

def send_startup_message():
    """Anuncia status do sistema."""
    pairs_txt = " | ".join([PAIR_CONFIGS[p]["symbol"] for p in WATCHLIST + WATCHLIST_EUR])
    
    message = (
        f"<b>✅ SISTEMA ONLINE</b>\n"
        f"{'═' * 30}\n"
        f"🔌 Conectividade: ✓\n"
        f"📊 TradingView: ✓ 15m/1h/4h/1d\n"
        f"🧠 Algoritmo: ✓ Calibrado\n"
        f"📈 Gráficos: ✓ Elite\n"
        f"🧱 Pivôs: ✓ Ativo\n"
        f"👑 Dominância: ✓ Live\n"
        f"🛡️ Gestão Risco: ✓ Ativa\n"
        f"📱 Telegran: ✓ Conectado\n"
        f"{'═' * 30}\n"
        f"\n<b>₿ PARES MONITORADOS</b>\n"
        f"{pairs_txt}\n"
        f"\n<b>⏰ AGENDA</b>\n"
        f"🔄 Sinais: 30 min\n"
        f"📰 Notícias: 2h\n"
        f"📊 Resumo: 08:00 UTC\n"
        f"{'═' * 30}\n"
        f"⚑ {random.choice(EXECUTIVE_INSIGHTS)}"
    )
    
    try:
        bot.send_message(CHAT_ID, message)
    except Exception as e:
        print(f"Erro ao enviar startup: {e}")

# ╔══════════════════════════════════════════════════════════════╗
# ║                     SCHEDULER ORCHESTRATION                 ║
# ╚══════════════════════════════════════════════════════════════╝

def scheduler_loop():
    """Execute scheduled operations at specified intervals."""
    schedule.every(30).minutes.do(scan_all_bitcoin_pairs)
    schedule.every(2).hours.do(send_crypto_news)
    schedule.every().day.at("08:00").do(send_daily_summary)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# ╔══════════════════════════════════════════════════════════════╗
# ║                    FLASK WEBHOOK HANDLER                    ║
# ╚══════════════════════════════════════════════════════════════╝

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data(as_text=True)
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "⭐ Bot Bitcoin Institucional — Online ⭐", 200

# ╔══════════════════════════════════════════════════════════════╗
# ║                      MAIN EXECUTION                         ║
# ╚══════════════════════════════════════════════════════════════╝

if __name__ == "__main__":
    print("🚀 Iniciando Sistema Bitcoin Institucional…")
    print("⏳ Carregando módulos…")
    
    bot.remove_webhook()
    time.sleep(2)
    
    if WEBHOOK_URL:
        webhook_full = f"{WEBHOOK_URL}/{TOKEN}"
        bot.set_webhook(url=webhook_full)
        print(f"✅ Webhook: {webhook_full}")
    else:
        print("⚠️ RAILWAY_STATIC_URL não definida. Modo polling.")
    
    send_startup_message()
    threading.Thread(target=scheduler_loop, daemon=True).start()
    
    if WEBHOOK_URL:
        port = int(os.environ.get("PORT", 8080))
        print(f"🌐 Flask rodando na porta {port}…")
        app.run(host="0.0.0.0", port=port)
    else:
        print("📡 Polling ativo…")
        while True:
            try:
                bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
            except Exception as e:
                print(f"⚠️ Erro: {e}. Reiniciando…")
                time.sleep(15)
