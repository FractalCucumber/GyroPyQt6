import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

app = QtGui.QApplication([])

win = pg.GraphicsWindow(title="Bar Graph with Tooltips")
plot = win.addPlot()

x = [1, 2, 3, 4, 5]
y = [5, 9, 7, 12, 8]

bar_item = pg.BarGraphItem(x=x, height=y, width=0.6, brush='b')
plot.addItem(bar_item)

def show_tooltip(event):
    pos = event[0]
    mouse_point = plot.vb.mapSceneToView(pos)
    # mouse_point = event.mapFromScene(event.scenePos())
    print(type(mouse_point))
    print(type(pos))
    print(type(event))
    index = int(mouse_point.x())
    p = win.mapToGlobal(pos.toPoint())
    if 0 <= index < len(x):
        tooltip = f"X: {x[index]}, Y: {y[index]}"
        QtGui.QToolTip.showText(p, tooltip)
    else:
        QtGui.QToolTip.hideText()
    print(1)

proxy_amp = pg.SignalProxy(
    plot.scene().sigMouseMoved, delay=0,
    rateLimit=12, slot=show_tooltip)
# plot.getViewBox().scene().sigMouseMoved.connect(show_tooltip)

app.exec_()