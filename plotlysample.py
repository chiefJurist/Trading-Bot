import matplotlib.pyplot as plt

# Sample data
data = {
    'x': ['2024-12-21 04:27:00', '2024-12-21 04:28:00', '2024-12-21 04:29:00'],
    'y': [100, 200, 150],
}

# Convert x to a more readable format (optional)
# If you want to handle time, you can use `matplotlib.dates` or just keep them as strings for simplicity

# Create a figure and axis
fig, ax = plt.subplots()

# Plot the data
ax.plot(data['x'], data['y'], marker='o', linestyle='-', color='b', label='Test Line')

# Set titles and labels
ax.set_title('Simple Line Chart')
ax.set_xlabel('Time')
ax.set_ylabel('Value')

# Rotate the x-axis labels for better readability (if needed)
plt.xticks(rotation=45)

# Display the chart
plt.tight_layout()  # Adjust layout to prevent clipping of labels
plt.show()
