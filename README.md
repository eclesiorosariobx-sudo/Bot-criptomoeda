# 🤖 Bot Criptomoeda - Sistema de Trading Telegram

Bot automatizado de trading para criptomoedas com análise técnica, sinais de compra/venda e notícias do mercado em tempo real.

## 🚀 Funcionalidades

- 📊 **Análise Técnica** - Integração com TradingView para análise de gráficos
- 🎯 **Sinais de Trade** - Detecção automática de oportunidades BTC/USDT (a cada 30 minutos)
- 📈 **Gráficos Premium** - Gráficos de candela com análise institucional
- 📰 **Notícias Crypto** - Radar do mercado com notícias atualizadas (a cada 2 horas)
- 💬 **Mensagens Motivacionais** - Citações inspiradoras sobre trading
- ⏱️ **Monitoramento 24h** - Funcionamento contínuo com scheduling automático

## 📋 Requisitos

- Python 3.11+
- Token do Telegram Bot
- Chat ID do Telegram
- Conexão com internet

## 🛠️ Instalação Local

```bash
# Clone o repositório
git clone https://github.com/eclesiorosariobx-sudo/Bot-criptomoeda.git
cd Bot-criptomoeda

# Crie um ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: venv\\Scripts\\activate

# Instale as dependências
pip install -r requirements.txt
```

## 🔑 Configuração

### Variáveis de Ambiente

Edite o arquivo `main.py` e configure:

```python
TOKEN = "seu_token_telegram_aqui"
CHAT_ID = "seu_chat_id_aqui"
```

**Ou use variáveis de ambiente:**

```bash
export TELEGRAM_TOKEN="seu_token"
export TELEGRAM_CHAT_ID="seu_chat_id"
```

### Como obter o Token

1. Fale com [@BotFather](https://t.me/botfather) no Telegram
2. Use `/newbot` para criar um novo bot
3. Copie o token fornecido

### Como obter o Chat ID

1. Fale com [@userinfobot](https://t.me/userinfobot)
2. Copie seu ID (use um grupo para um Group Chat ID)

## ▶️ Executar Localmente

```bash
python main.py
```

## 🚀 Deploy no Railway

### Pré-requisitos

- Conta no [Railway](https://railway.app)
- Repositório GitHub com este código

### Passos

1. **Conecte seu GitHub ao Railway**
   - Acesse railway.app
   - Clique em "New Project"
   - Selecione "Deploy from GitHub repo"

2. **Configure as Variáveis de Ambiente**
   - Na dashboard do Railway
   - Acesse a aba "Variables"
   - Adicione:
     ```
     TELEGRAM_TOKEN=seu_token_aqui
     TELEGRAM_CHAT_ID=seu_chat_id_aqui
     ```

3. **Deploy Automático**
   - Railway detectará o `Procfile` e `runtime.txt`
   - O deploy será feito automaticamente
   - Acompanhe os logs na dashboard

## 📊 Horários de Funcionamento

- **Sinais de Trade**: A cada 30 minutos
- **Notícias**: A cada 2 horas
- **Monitoramento**: 24/7

## ⚠️ Avisos Importantes

⚠️ **Risco Financeiro**: Este bot é para fins educacionais. Trading em criptomoedas envolve alto risco. Use apenas com capital que possa perder.

⚠️ **Gestão de Risco**: O bot recomenda usar no máximo 1-2% da sua banca em cada operação.

⚠️ **Responsabilidade**: O desenvolvedor não se responsabiliza por perdas financeiras.

## 📁 Estrutura do Projeto

```
.
├── main.py           # Script principal do bot
├── requirements.txt   # Dependências Python
├── Procfile          # Configuração para Railway
├── runtime.txt       # Versão Python
└── README.md         # Este arquivo
```

## 🔧 Tecnologias Utilizadas

- **pyTelegramBotAPI** - Integração com Telegram
- **CCXT** - API para dados de criptomoedas
- **TradingView-TA** - Análise técnica
- **mplfinance** - Gráficos de candela
- **Feedparser** - Parsing de RSS feeds
- **Schedule** - Agendamento de tarefas

## 📞 Suporte

Em caso de dúvidas ou problemas:
- Verifique os logs do Railway
- Confirme que as variáveis de ambiente estão corretas
- Verifique a conexão com a internet

## 📝 Licença

Este projeto é fornecido como está, para fins educacionais.

---

**Desenvolvido por**: Análise Algorítmica Institucional 🚀
