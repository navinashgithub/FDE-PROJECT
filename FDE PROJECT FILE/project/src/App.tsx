import { useEffect, useState } from 'react';
import { TrendingUp, Activity, AlertCircle, Zap, Globe } from 'lucide-react';

interface HealthStatus {
  status: string;
  components: {
    redis: string;
    timescaledb: string;
    influxdb: string;
  };
}

interface PricePoint {
  timestamp: number;
  price: number;
}

function App() {
  const [latestPrices, setLatestPrices] = useState<Record<string, number>>({});
  const [priceHistory, setPriceHistory] = useState<Record<string, PricePoint[]>>({
    AAPL: [],
    GOOGL: [],
    MSFT: [],
    AMZN: [],
    TSLA: [],
  });
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL');
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiBase = 'http://127.0.0.1:8000';
  const wsBase = 'ws://127.0.0.1:8002';

  const handleWebSocketMessage = (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      if (data.symbol && typeof data.price === 'number') {
        setLatestPrices((prev) => ({
          ...prev,
          [data.symbol]: data.price,
        }));
        
        // Add to price history
        setPriceHistory((prev) => {
          const newHistory = { ...prev };
          const timestamp = Date.now();
          const newPoint: PricePoint = { timestamp, price: data.price };
          
          newHistory[data.symbol] = [...(newHistory[data.symbol] || []), newPoint];
          
          // Keep only last 60 points
          if (newHistory[data.symbol].length > 60) {
            newHistory[data.symbol] = newHistory[data.symbol].slice(-60);
          }
          
          return newHistory;
        });
      }
    } catch (e) {
      console.error('Failed to parse message:', e);
    }
  };

  const getConnectionStatusText = (): string => {
    if (loading) return 'Loading...';
    return wsConnected ? 'Live' : 'Offline';
  };

  // Fetch health status on mount
  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await fetch(`${apiBase}/health`);
        if (!response.ok) throw new Error('Health check failed');
        const data = await response.json();
        setHealthStatus(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to connect to backend');
        setLoading(false);
      }
    };

    fetchHealth();
    const healthInterval = setInterval(fetchHealth, 10000); // Poll every 10s
    return () => clearInterval(healthInterval);
  }, []);

  // WebSocket connection for real-time data
  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;
    const symbolsList = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'];

    const connectWebSocket = () => {
      try {
        ws = new WebSocket(wsBase);

        ws.onopen = () => {
          console.log('WebSocket connected');
          setWsConnected(true);
          setLoading(false);
          setError(null);

          // Subscribe to all symbols
          const subscribeMsg = {
            type: 'subscribe',
            symbols: symbolsList,
          };
          ws.send(JSON.stringify(subscribeMsg));
        };

        ws.onmessage = (event) => {
          handleWebSocketMessage(event);
        };

        ws.onerror = (event) => {
          console.error('WebSocket error:', event);
          setError('WebSocket connection error');
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected');
          setWsConnected(false);
          // Attempt reconnection after 3 seconds
          reconnectTimeout = setTimeout(connectWebSocket, 3000);
        };
      } catch (err) {
        console.error('WebSocket connection failed:', err);
        setError('Failed to connect to WebSocket');
        reconnectTimeout = setTimeout(connectWebSocket, 3000);
      }
    };

    connectWebSocket();

    return () => {
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  const currentPrice = latestPrices[selectedSymbol];

  // Helper to get last element of array
  const getLast = <T,>(arr: T[]): T | undefined => {
    return arr[arr.length - 1];
  };

  // Calculate price stats for a symbol
  const getSymbolStats = (symbol: string) => {
    const history = priceHistory[symbol] || [];
    if (history.length === 0) return null;
    
    const prices = history.map(p => p.price);
    const currentPrice = getLast(prices) || 0;
    const previousPrice = prices[0] || 0;
    const change = currentPrice - previousPrice;
    const changePercent = previousPrice > 0 ? ((change / previousPrice) * 100) : 0;
    const high = Math.max(...prices);
    const low = Math.min(...prices);
    
    return {
      currentPrice,
      previousPrice,
      change,
      changePercent,
      high,
      low,
      history
    };
  };

  // Render a mini chart using SVG
  const renderMiniChart = (symbol: string, width = 200, height = 100) => {
    const stats = getSymbolStats(symbol);
    if (!stats || stats.history.length < 2) return null;

    const prices = stats.history.map(p => p.price);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice || 1;

    // Create SVG path for the chart line
    const points = prices.map((price, index) => {
      const x = (index / (prices.length - 1)) * width;
      const y = height - ((price - minPrice) / priceRange) * height;
      return `${x},${y}`;
    }).join(' ');

    const isPositive = stats.change >= 0;
    const lineColor = isPositive ? '#10b981' : '#ef4444';
    const fillColor = isPositive ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';

    return (
      <svg width={width} height={height} className="w-full h-full">
        {/* Background fill */}
        <polyline
          points={`0,${height} ${points} ${width},${height}`}
          fill={fillColor}
          stroke="none"
        />
        {/* Line */}
        <polyline
          points={points}
          fill="none"
          stroke={lineColor}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-800/50 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-gradient-to-br from-blue-500 to-cyan-500 p-2 rounded-lg">
                <Globe className="h-8 w-8 text-white" />
              </div>
              <h1 className="text-3xl font-bold text-white">
                Real-Time Market Data Streaming
              </h1>
            </div>
            <div className="flex items-center gap-2">
              <div
                className={`h-3 w-3 rounded-full ${
                  wsConnected ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              <span className="text-sm font-medium text-slate-300">
                {wsConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Error Alert */}
        {error && (
          <div className="mb-6 bg-red-500/10 border border-red-500/30 rounded-lg p-4 flex items-gap-3">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-medium text-red-100">Connection Error</h3>
              <p className="text-sm text-red-200 mt-1">{error}</p>
              <p className="text-xs text-red-300 mt-2">
                Make sure the backend services (FastAPI REST API on port 8000 and WebSocket server on port 8001) are running.
              </p>
            </div>
          </div>
        )}

        {/* Health Status Cards */}
        {healthStatus && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            {Object.entries(healthStatus.components).map(([component, status]) => (
              <div
                key={component}
                className="bg-slate-700/50 border border-slate-600 rounded-lg p-4"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-slate-300 capitalize">
                    {component.replace('_', ' ')}
                  </h3>
                  <div
                    className={`h-2.5 w-2.5 rounded-full ${
                      status === 'healthy' ? 'bg-green-500' : 'bg-yellow-500'
                    }`}
                  />
                </div>
                <p className="text-lg font-semibold text-white capitalize mt-1">
                  {status}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Symbol Selector & Price Display */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Left: Symbol Selector */}
          <div className="lg:col-span-1">
            <div className="bg-slate-700/50 border border-slate-600 rounded-lg p-6">
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Activity className="h-5 w-5 text-blue-400" />
                Select Symbol
              </h2>
              <div className="space-y-2">
                {['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'].map((symbol) => (
                  <button
                    key={symbol}
                    onClick={() => setSelectedSymbol(symbol)}
                    className={`w-full px-4 py-2 rounded-lg font-medium transition-all text-left ${
                      selectedSymbol === symbol
                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                        : 'bg-slate-600/50 text-slate-300 hover:bg-slate-600 hover:text-white'
                    }`}
                  >
                    {symbol}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Right: Price Display */}
          <div className="lg:col-span-2">
            <div className="bg-gradient-to-br from-slate-700/50 to-slate-800/50 border border-slate-600 rounded-lg p-8">
              <h2 className="text-lg font-semibold text-slate-300 mb-2">
                Current Price
              </h2>
              <div className="flex items-baseline gap-3">
                <h1 className="text-5xl font-bold text-white">
                  {currentPrice ? `$${currentPrice.toFixed(2)}` : '--'}
                </h1>
                <span className="text-lg text-slate-400">USD</span>
              </div>
              <p className="text-slate-400 mt-6 text-sm">
                Symbol: <span className="font-semibold text-slate-200">{selectedSymbol}</span>
              </p>
              <p className="text-slate-400 text-sm">
                Status:{' '}
                <span
                  className={`font-semibold ${
                    wsConnected ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {getConnectionStatusText()}
                </span>
              </p>
            </div>
          </div>
        </div>

        {/* Stock Charts Grid */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-green-400" />
            All Stocks - Real-Time Charts
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'].map((symbol) => {
              const stats = getSymbolStats(symbol);
              const currentPrice = latestPrices[symbol] || 0;
              const isPositive = stats ? stats.change >= 0 : false;
              
              let changePercentText = '--';
              if (stats) {
                const sign = isPositive ? '+' : '';
                changePercentText = `${sign}${stats.changePercent.toFixed(2)}%`;
              }

              return (
                <button
                  key={symbol}
                  onClick={() => setSelectedSymbol(symbol)}
                  className={`text-left bg-slate-700/50 border rounded-lg p-4 transition-all hover:border-blue-400 ${
                    selectedSymbol === symbol
                      ? 'border-blue-500 ring-2 ring-blue-500/20'
                      : 'border-slate-600 hover:border-slate-500'
                  }`}
                >
                  {/* Symbol and Price */}
                  <div className="mb-3">
                    <div className="flex items-start justify-between mb-1">
                      <h3 className="text-lg font-bold text-white">{symbol}</h3>
                      <span className={`text-xs font-semibold px-2 py-1 rounded ${
                        isPositive
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-red-500/20 text-red-400'
                      }`}>
                        {changePercentText}
                      </span>
                    </div>
                    <div className="text-2xl font-bold text-white">
                      ${currentPrice.toFixed(2)}
                    </div>
                  </div>

                  {/* Chart */}
                  <div className="mb-3 h-16 bg-slate-800/50 rounded border border-slate-600">
                    {stats && stats.history.length > 1 ? (
                      renderMiniChart(symbol, 300, 64)
                    ) : (
                      <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                        Loading...
                      </div>
                    )}
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-slate-400">High</p>
                      <p className="text-slate-200 font-semibold">
                        ${stats ? stats.high.toFixed(2) : '--'}
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-400">Low</p>
                      <p className="text-slate-200 font-semibold">
                        ${stats ? stats.low.toFixed(2) : '--'}
                      </p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* System Info */}
        <div className="bg-slate-700/50 border border-slate-600 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Zap className="h-5 w-5 text-yellow-400" />
            System Information
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-slate-300">
            <div>
              <p className="font-medium text-slate-200">Backend Services</p>
              <ul className="list-disc list-inside mt-2 space-y-1 text-xs">
                <li>REST API: http://127.0.0.1:8000</li>
                <li>WebSocket: ws://127.0.0.1:8002</li>
                <li>Dashboard: http://127.0.0.1:8050</li>
              </ul>
            </div>
            <div>
              <p className="font-medium text-slate-200">Data Sources</p>
              <ul className="list-disc list-inside mt-2 space-y-1 text-xs">
                <li>Polygon.io (WebSocket)</li>
                <li>Finage (REST/WebSocket)</li>
                <li>Alpha Vantage (REST)</li>
                <li>Financial Modeling Prep (REST)</li>
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
