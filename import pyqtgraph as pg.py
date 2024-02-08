import pyqtgraph as pg
from PyQt5 import QtGui

app = QtGui.QApplication([])

plot_window = pg.plot()
plot_window.setWindowTitle('Tooltip Example')

# Your plotting code here
# plot_window.plot(...) or any other plotting commands

plot_item = plot_window.plot([1, 2, 3], [4, 5, 6], pen=pg.mkPen((205, 205, 205), dash=[15, 3], width=10))  # Example plot data

# Add a tooltip to the plot_item
# plot_item.getPlotItem().curves[i].setToolTip('This is a red line.')
plot_item.curves[0].setToolTip('This is a red line.')

# You can also add tooltips to other plot elements in a similar way
# For example, if you're adding scatter points
scatter_item = pg.ScatterPlotItem(x=[2], y=[5], symbol='o', size=10, pen='b', brush='b')
scatter_item.setToolTip('This is a blue circle.')
plot_window.addItem(scatter_item)

# Show the plot
plot_window.show()

app.exec()