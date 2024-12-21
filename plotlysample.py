import plotly.graph_objects as go

# Sample data
data = {
    'x': ['2024-12-21 04:27:00', '2024-12-21 04:28:00', '2024-12-21 04:29:00'],
    'y': [100, 200, 150],
}

# Create a simple line chart
fig = go.Figure(data=go.Scatter(x=data['x'], y=data['y'], mode='lines+markers', name='Test Line'))

# Update layout for better visuals
fig.update_layout(
    title='Simple Line Chart',
    xaxis_title='Time',
    yaxis_title='Value',
    template='plotly_dark'
)

# Display the chart
fig.show()