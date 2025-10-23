import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from datetime import datetime, timedelta
import pandas as pd
import requests
from src.utils.config_loader import settings
from src.storage.redis_cache import RedisCache
from src.storage.influxdb_handler import InfluxDBHandler

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

redis_cache = RedisCache()
influx_db = InfluxDBHandler()

symbols = settings.symbols.split(',')

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("📈 Real-Time Market Data Dashboard", className="text-center mb-4 mt-4"),
            html.P("Live streaming financial market data with technical indicators",
                   className="text-center text-muted mb-4")
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id='symbol-selector',
                options=[{'label': symbol, 'value': symbol} for symbol in symbols],
                value=symbols[0],
                clearable=False,
                className="mb-3"
            )
        ], width=6),
        dbc.Col([
            dcc.Dropdown(
                id='window-selector',
                options=[
                    {'label': '1 Minute', 'value': '1min'},
                    {'label': '5 Minutes', 'value': '5min'},
                    {'label': '15 Minutes', 'value': '15min'}
                ],
                value='1min',
                clearable=False,
                className="mb-3"
            )
        ], width=6)
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Current Price", className="card-title"),
                    html.H2(id="current-price", children="--", className="text-success"),
                    html.P(id="price-change", children="--", className="text-muted")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Volume", className="card-title"),
                    html.H2(id="current-volume", children="--", className="text-info"),
                    html.P("24h Volume", className="text-muted")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("RSI", className="card-title"),
                    html.H2(id="current-rsi", children="--", className="text-warning"),
                    html.P(id="rsi-signal", children="--", className="text-muted")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("VWAP", className="card-title"),
                    html.H2(id="current-vwap", children="--", className="text-primary"),
                    html.P("Volume Weighted", className="text-muted")
                ])
            ])
        ], width=3)
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            dcc.Graph(id='price-chart', style={'height': '400px'})
        ], width=12)
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            dcc.Graph(id='volume-chart', style={'height': '300px'})
        ], width=6),
        dbc.Col([
            dcc.Graph(id='indicators-chart', style={'height': '300px'})
        ], width=6)
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            dcc.Graph(id='latency-chart', style={'height': '250px'})
        ], width=12)
    ]),

    dcc.Interval(
        id='interval-component',
        interval=2000,
        n_intervals=0
    )
], fluid=True, style={'backgroundColor': '#1a1a1a'})


@app.callback(
    [Output('current-price', 'children'),
     Output('price-change', 'children'),
     Output('current-volume', 'children'),
     Output('current-rsi', 'children'),
     Output('rsi-signal', 'children'),
     Output('current-vwap', 'children')],
    [Input('interval-component', 'n_intervals'),
     Input('symbol-selector', 'value')]
)
def update_metrics(n, symbol):
    try:
        latest_price_data = redis_cache.get_latest_price(symbol)
        indicators = redis_cache.get_technical_indicators(symbol)

        if not latest_price_data:
            return "--", "--", "--", "--", "--", "--"

        price = latest_price_data.get('price', 0)
        volume = latest_price_data.get('volume', 0)

        price_display = f"${price:.2f}"
        volume_display = f"{volume:,.0f}"

        rsi = indicators.get('rsi', 0) if indicators else 0
        rsi_display = f"{rsi:.1f}" if rsi else "--"

        rsi_signal = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"

        agg_data = redis_cache.get_aggregated_data(symbol, '1min')
        vwap = agg_data.get('vwap', 0) if agg_data else 0
        vwap_display = f"${vwap:.2f}" if vwap else "--"

        return price_display, "↑ +2.5%", volume_display, rsi_display, rsi_signal, vwap_display

    except Exception as e:
        return "--", "--", "--", "--", "--", "--"


@app.callback(
    Output('price-chart', 'figure'),
    [Input('interval-component', 'n_intervals'),
     Input('symbol-selector', 'value'),
     Input('window-selector', 'value')]
)
def update_price_chart(n, symbol, window):
    try:
        records = influx_db.query_aggregated_metrics(symbol, window, time_range="-1h")

        if not records:
            return go.Figure().update_layout(
                title=f"{symbol} Price Chart (No Data)",
                template="plotly_dark"
            )

        df = pd.DataFrame(records)

        if '_time' in df.columns:
            df['time'] = pd.to_datetime(df['_time'])
            df = df.sort_values('time')

            fig = go.Figure()

            fig.add_trace(go.Candlestick(
                x=df['time'],
                open=df.get('open', []),
                high=df.get('high', []),
                low=df.get('low', []),
                close=df.get('close', []),
                name='OHLC'
            ))

            if 'vwap' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df['time'],
                    y=df['vwap'],
                    mode='lines',
                    name='VWAP',
                    line=dict(color='orange', width=2)
                ))

            fig.update_layout(
                title=f"{symbol} - {window} Candlestick with VWAP",
                xaxis_title="Time",
                yaxis_title="Price ($)",
                template="plotly_dark",
                xaxis_rangeslider_visible=False,
                hovermode='x unified'
            )

            return fig

    except Exception as e:
        pass

    return go.Figure().update_layout(title=f"{symbol} Price Chart", template="plotly_dark")


@app.callback(
    Output('volume-chart', 'figure'),
    [Input('interval-component', 'n_intervals'),
     Input('symbol-selector', 'value'),
     Input('window-selector', 'value')]
)
def update_volume_chart(n, symbol, window):
    try:
        records = influx_db.query_aggregated_metrics(symbol, window, time_range="-1h")

        if not records:
            return go.Figure().update_layout(title="Volume (No Data)", template="plotly_dark")

        df = pd.DataFrame(records)

        if '_time' in df.columns and 'volume' in df.columns:
            df['time'] = pd.to_datetime(df['_time'])
            df = df.sort_values('time')

            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=df['time'],
                y=df['volume'],
                name='Volume',
                marker_color='lightblue'
            ))

            fig.update_layout(
                title=f"{symbol} - Volume",
                xaxis_title="Time",
                yaxis_title="Volume",
                template="plotly_dark"
            )

            return fig

    except Exception as e:
        pass

    return go.Figure().update_layout(title="Volume", template="plotly_dark")


@app.callback(
    Output('indicators-chart', 'figure'),
    [Input('interval-component', 'n_intervals'),
     Input('symbol-selector', 'value')]
)
def update_indicators_chart(n, symbol):
    try:
        records = influx_db.query_latest_metrics(symbol, "technical_indicators", time_range="-1h")

        if not records:
            return go.Figure().update_layout(title="Technical Indicators (No Data)", template="plotly_dark")

        df = pd.DataFrame(records)
        df['time'] = pd.to_datetime(df['time'])

        rsi_data = df[df['field'] == 'rsi'].sort_values('time')

        fig = go.Figure()

        if not rsi_data.empty:
            fig.add_trace(go.Scatter(
                x=rsi_data['time'],
                y=rsi_data['value'],
                mode='lines',
                name='RSI',
                line=dict(color='yellow', width=2)
            ))

            fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
            fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")

        fig.update_layout(
            title=f"{symbol} - RSI Indicator",
            xaxis_title="Time",
            yaxis_title="RSI",
            template="plotly_dark",
            yaxis=dict(range=[0, 100])
        )

        return fig

    except Exception as e:
        pass

    return go.Figure().update_layout(title="Technical Indicators", template="plotly_dark")


@app.callback(
    Output('latency-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_latency_chart(n):
    try:
        records = influx_db.query_latest_metrics("", "latency_metrics", time_range="-5m")

        if not records:
            return go.Figure().update_layout(title="System Latency (No Data)", template="plotly_dark")

        df = pd.DataFrame(records)
        df['time'] = pd.to_datetime(df['time'])

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df['time'],
            y=df['value'],
            mode='lines+markers',
            name='Latency',
            line=dict(color='cyan', width=2)
        ))

        fig.add_hline(
            y=settings.processing_latency_threshold_ms,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Threshold ({settings.processing_latency_threshold_ms}ms)"
        )

        fig.update_layout(
            title="End-to-End Processing Latency",
            xaxis_title="Time",
            yaxis_title="Latency (ms)",
            template="plotly_dark"
        )

        return fig

    except Exception as e:
        pass

    return go.Figure().update_layout(title="System Latency", template="plotly_dark")


def main():
    app.run_server(
        host='0.0.0.0',
        port=8050,
        debug=False
    )


if __name__ == '__main__':
    main()
