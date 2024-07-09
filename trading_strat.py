import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt

class RSIStrategy(bt.Strategy):
    params = (('rsi_period', 14), ('rsi_overbought', 70), ('rsi_oversold', 30))

    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)

    def next(self):
        if not self.position:
            if self.rsi < self.params.rsi_oversold:
                cash = self.broker.getcash()
                shares = int(cash / self.data.close[0])
                self.buy(size=shares)
        elif self.rsi > self.params.rsi_overbought:
            self.close()

class BollingerBandsStrategy(bt.Strategy):
    params = (('period', 20), ('devfactor', 2))

    def __init__(self):
        self.bband = bt.indicators.BollingerBands(self.data.close, period=self.params.period, devfactor=self.params.devfactor)

    def next(self):
        if not self.position:
            if self.data.close[0] < self.bband.lines.bot[0]:
                cash = self.broker.getcash()
                shares = int(cash / self.data.close[0])
                self.buy(size=shares)
        elif self.data.close[0] > self.bband.lines.top[0]:
            self.close()

class MovingAverageCrossoverStrategy(bt.Strategy):
    params = (('fast', 10), ('slow', 30))

    def __init__(self):
        self.fast_ma = bt.indicators.SMA(self.data.close, period=self.params.fast)
        self.slow_ma = bt.indicators.SMA(self.data.close, period=self.params.slow)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                cash = self.broker.getcash()
                shares = int(cash / self.data.close[0])
                self.buy(size=shares)
        elif self.crossover < 0:
            self.close()

class TradeAnalyzer(bt.Analyzer):
    def __init__(self):
        self.trades = 0
        self.wins = 0

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trades += 1
            if trade.pnl > 0:
                self.wins += 1

    def get_analysis(self):
        return {
            "total_trades": self.trades,
            "wins": self.wins,
            "win_rate": (self.wins / self.trades) if self.trades > 0 else 0
        }

def load_data():
    df = pd.read_csv('historical_data.csv')
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    return df

def run_strategy(strategy_class):
    cerebro = bt.Cerebro()
    data = load_data()
    feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(feed)
    cerebro.addstrategy(strategy_class)
    cerebro.broker.setcash(100000)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(TradeAnalyzer, _name='trade_analyzer')

    print(f'Running {strategy_class.__name__}:')
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    results = cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    strat = results[0]
    print('Sharpe Ratio:', strat.analyzers.sharpe_ratio.get_analysis().get('sharperatio', 'N/A'))
    print('Annual Return:', strat.analyzers.returns.get_analysis().get('rnorm100', 'N/A'))
    print('Max Drawdown:', strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 'N/A'))

    trade_analysis = strat.analyzers.trade_analyzer.get_analysis()
    total_trades = trade_analysis.get('total_trades', 0)
    wins = trade_analysis.get('wins', 0)
    win_rate = trade_analysis.get('win_rate', 0)

    print(f"Total Trades: {total_trades}")
    print(f"Winning Trades: {wins}")
    print(f"Win Rate: {win_rate:.2%}")
    print('\n')
    # Plot the results
    cerebro.plot(style='candle')

    return results

# Load and check data
data = load_data()

# Run all strategies
rsi_results = run_strategy(RSIStrategy)
bb_results = run_strategy(BollingerBandsStrategy)
ma_results = run_strategy(MovingAverageCrossoverStrategy)

# Plot the results
plt.figure(figsize=(12, 6))
plt.subplot(131)
bt.plot.plot_returns(rsi_results[0])
plt.title('RSI Strategy Returns')
plt.subplot(132)
bt.plot.plot_returns(bb_results[0])
plt.title('Bollinger Bands Strategy Returns')
plt.subplot(133)
bt.plot.plot_returns(ma_results[0])
plt.title('MA Crossover Strategy Returns')
plt.tight_layout()
plt.show()