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

TOKEN = "7734730548:AAHM8SufT9OuA0KoYRGglf24Vm8kQTCrpbA"
CHAT_ID = "-1003780528406"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

MOTIVACOES = [
"💎 <b>O mercado transfere dinheiro dos impacientes para os pacientes.</b>",
"🚀 <b>Traders amadores focam nos lucros. Profissionais focam em proteger o capital.</b>",
"🦅 <b>A disciplina e a ponte entre a meta e a realizacao.</b>",
"🔥 <b>Um dia ruim de trade nao define sua carreira.</b>",
"👑 <b>O sucesso no mercado financeiro e 20% estrategia e 80% psicologia.</b>"
]

def get_tradingview_analysis(symbol="BTCUSDT"):
	try:
		handler = TA_Handler(
			symbol=symbol,
			screener="crypto",
			exchange="BINANCE",
			interval=Interval.INTERVAL_1_HOUR
		)
		analysis = handler.get_analysis()
		return analysis.summary["RECOMMENDATION"], analysis.indicators["close"]
	except Exception as e:
		print("Erro TV: " + str(e))
		return "NEUTRAL", 0

def generate_premium_chart():
	try:
		exchange = ccxt.binance()
		bars = exchange.fetch_ohlcv("BTC/USDT", timeframe="1h", limit=100)
		df = pd.DataFrame(bars, columns=["time", "open", "high", "low", "close", "volume"])
		df["time"] = pd.to_datetime(df["time"], unit="ms")
		df.set_index("time", inplace=True)

		mc = mpf.make_marketcolors(up="#089981", down="#F23645", inherit=True)
		s = mpf.make_mpf_style(
			marketcolors=mc,
			gridstyle="dotted",
			y_on_right=True,
			facecolor="#131722",
			edgecolor="#363c4e",
			figcolor="#131722",
			rc={
				"text.color": "#D1D4DC",
				"axes.labelcolor": "#D1D4DC",
				"xtick.color": "#D1D4DC",
				"ytick.color": "#D1D4DC"
			}
		)

		chart_filename = "premium_chart.png"
		mpf.plot(df, type="candle", volume=True, mav=(9, 21), style=s,
		         title="\nBTC/USDT - Analise Algoritmica Institucional (1H)",
		         savefig=chart_filename, figsize=(12, 6))
		return chart_filename
	except Exception as e:
		print("Erro ao gerar grafico: " + str(e))
		return None

def send_trade_signal():
	recommendation, current_price = get_tradingview_analysis()

	if "BUY" in recommendation or "SELL" in recommendation:
		is_buy = "BUY" in recommendation
		trade_type = "🟢 COMPRA (LONG)" if is_buy else "🔴 VENDA (SHORT)"
		emoji = "📈" if is_buy else "📉"

		if is_buy:
			tp = current_price * 1.02
			sl = current_price * 0.99
		else:
			tp = current_price * 0.98
			sl = current_price * 1.01

		chart_file = generate_premium_chart()

		message = (
			emoji + "<b>OPORTUNIDADE DETECTADA NO GRAFICO</b>" + emoji + "\n"
			+ "<i>Desenvolvido por Analise Algoritmica</i>\n"
			+ "💎 <b>Ativo:</b> #BTC/USDT\n"
			+ "🎯 <b>Operacao:</b> " + trade_type + "\n"
			+ "💰 <b>Entrada (Mercado):</b> $" + "{:,.2f}".format(current_price) + "\n"
			+ "✅ <b>Take Profit (Alvo):</b> $" + "{:,.2f}".format(tp) + "\n"
			+ "❌ <b>Stop Loss (Risco):</b> $" + "{:,.2f}".format(sl) + "\n"
			+ "⚠️ <i>Utilize no maximo 1% a 2% da sua banca nesta entrada.</i>"
		)

		try:
			if chart_file and os.path.exists(chart_file):
				with open(chart_file, "rb") as photo:
					bot.send_photo(CHAT_ID, photo, caption=message)
				os.remove(chart_file)
			else:
				bot.send_message(CHAT_ID, message)
		except Exception as e:
			print("Erro ao enviar sinal: " + str(e))

def send_crypto_news():
	try:
		feed = feedparser.parse("https://cointelegraph.com.br/rss")
		if feed.entries:
			entry = feed.entries[0]
			message = (
				"🌍 <b>RADAR DO MERCADO</b> 🌍\n"
				+ "📰 <b>" + entry.title + "</b>\n"
				+ "<i>" + entry.summary[:180] + "…</i>\n"
				+ "🔗 <a href=\"" + entry.link + "\">Ler materia completa</a>\n"
				+ "💡 " + random.choice(MOTIVACOES)
			)
			bot.send_message(CHAT_ID, message, disable_web_page_preview=False)
	except Exception as e:
		print("Erro ao buscar noticias: " + str(e))

def send_startup_message():
	startup_message = (
		"🟢 <b>SISTEMA DE TRADING INSTITUCIONAL ONLINE</b> 🟢\n"
		+ "⚙️ Conexao estabelecida com os servidores…\n"
		+ "📊 Modulos API TradingView: <b>[ ATIVOS ]</b>\n"
		+ "🧠 Algoritmo de Inteligencia e Graficos: <b>[ PRONTO ]</b>\n"
		+ "<i>A partir de agora, o mercado sera monitorado 24h.</i> 🥂"
	)
	try:
		bot.send_message(CHAT_ID, startup_message)
	except Exception as e:
		print("Erro ao enviar mensagem de inicializacao: " + str(e))

def scheduler_loop():
	schedule.every(2).hours.do(send_crypto_news)
	schedule.every(30).minutes.do(send_trade_signal)

	while True:
		schedule.run_pending()
		time.sleep(1)

if __name__ == "__main__":
	print("Iniciando Bot Premium…")

	bot.remove_webhook()
	time.sleep(3)

	send_startup_message()

	threading.Thread(target=scheduler_loop, daemon=True).start()

	while True:
		try:
			bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
		except Exception as e:
			print("Erro de conexao com Telegram. Reiniciando em 15s... Erro: " + str(e))
			time.sleep(15)
