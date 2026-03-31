import pyqtgraph as pg
import numpy as np
import networkx as nx
from PyQt5 import QtWidgets, QtGui, QtCore


def draw_tree(graph_widget, edges, node_names=None):
    graph_widget.clear()
    node_names = node_names or {}

    children_map = {}
    levels = {}
    for parent, child in edges:
        parent = str(parent)
        child = str(child)
        if parent not in children_map:
            children_map[parent] = []
        children_map[parent].append(child)

    def assign_levels(node, current_level=0):
        levels[node] = current_level
        for child in children_map.get(node, []):
            assign_levels(child, current_level + 1)

    all_nodes = set(str(parent) for parent, _ in edges) | set(str(child) for _, child in edges)
    child_nodes = set(str(child) for _, child in edges)
    root_nodes = all_nodes - child_nodes
    root = list(root_nodes)[0] if root_nodes else None

    if root is None:
        raise ValueError("Nie znaleziono korzenia drzewa!")

    assign_levels(root)
    positions = {}

    def calculate_positions(node, x_offset=0, y_offset=0, horizontal_gap=100):
        children = children_map.get(node, [])
        if not children:
            positions[node] = (x_offset, y_offset)
            return x_offset

        subtree_widths = []
        for child in children:
            width = calculate_positions(child, x_offset, y_offset - 100, horizontal_gap)
            subtree_widths.append(width)
            x_offset = width + horizontal_gap

        node_x = (subtree_widths[0] + subtree_widths[-1]) / 2
        positions[node] = (node_x, y_offset)
        return node_x

    calculate_positions(root, x_offset=0, y_offset=0)

    # TODO: Validate whether this is required
    if positions:
        x_values = [pos[0] for pos in positions.values()]
        y_values = [pos[1] for pos in positions.values()]
        x_min, x_max = min(x_values), max(x_values)
        y_min, y_max = min(y_values), max(y_values)
        
        x_padding = (x_max - x_min) * 0.2
        y_padding = (y_max - y_min) * 0.2
        
        graph_widget.setXRange(x_min - x_padding, x_max + x_padding)
        graph_widget.setYRange(y_min - y_padding, y_max + y_padding)

    for parent, child in edges:
        parent = str(parent)
        child = str(child)
        x1, y1 = positions[parent]
        x2, y2 = positions[child]
        graph_widget.plot([x1, x2], [y1, y2], pen=pg.mkPen('black', width=3))

    max_level = max(levels.values())

    base_size = 50
    min_size = 20
    size_scale = max(base_size - (max_level * 5), min_size) / base_size

    # Rysowanie węzłów
    for node, (x, y) in positions.items():
        node_size = base_size * size_scale

        graph_widget.plot(
            [x], [y], pen=None, symbol='o', symbolSize=node_size, symbolBrush='lightgreen'
        )
        text = pg.TextItem(str(node), anchor=(0.5, 0.5), color='black')
        text.setPos(x, y)
        graph_widget.addItem(text)

        state_name = node_names.get(node, None)
        if state_name:
            name_text = pg.TextItem(state_name, anchor=(0.5, 0), color='darkgreen')
            name_text.setPos(x, y-0.5)
            graph_widget.addItem(name_text)


class HoverScatterPlotItem(pg.ScatterPlotItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptHoverEvents(True)
        self.tooltip_text = kwargs.get('tooltip_text', '')
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_tooltip)
        self.timer.setInterval(100)

    def hoverEvent(self, ev):
        if ev.isEnter():
            self.timer.start()
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), self.tooltip_text)
        elif ev.isExit():
            self.timer.stop()
            QtWidgets.QToolTip.hideText()

    def update_tooltip(self):
        if self.isUnderMouse():
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), self.tooltip_text)
        else:
            self.timer.stop()
            QtWidgets.QToolTip.hideText()


def draw_state_machine(graph_widget, transitions, all_states):
    G = nx.DiGraph()
    for from_state, to_state, _ in transitions:
        G.add_edge(from_state, to_state)

    # Ustal pozycje dla wszystkich wierzchołków
    is_planar, embedding = nx.check_planarity(G)
    positions = nx.planar_layout(G) if is_planar else nx.spring_layout(G)

    scale = 200
    positions = {node: (pos[0] * scale, pos[1] * scale) for node, pos in positions.items()}

    graph_widget.clear()

    # TODO: Validate whether this is required
    if positions:
        x_values = [pos[0] for pos in positions.values()]
        y_values = [pos[1] for pos in positions.values()]
        x_min, x_max = min(x_values), max(x_values)
        y_min, y_max = min(y_values), max(y_values)
        
        x_padding = (x_max - x_min) * 0.2
        y_padding = (y_max - y_min) * 0.2
        
        graph_widget.setXRange(x_min - x_padding, x_max + x_padding)
        graph_widget.setYRange(y_min - y_padding, y_max + y_padding)

    seen_connections = {}
    for from_state, to_state, event in transitions:
        x1, y1 = positions[from_state]
        x2, y2 = positions[to_state]

        pair_key = (min(from_state, to_state), max(from_state, to_state))

        if pair_key not in seen_connections:
            seen_connections[pair_key] = 0
        seen_connections[pair_key] += 1
        curvature = seen_connections[pair_key] * 40

        label_html = f"""
                        <div style="background-color: white; border-radius: 3px; text-align: center;">
                            <span style="font-size: 14px; color: red; font-weight: bold;">{event}</span>
                        </div>
                    """

        if from_state == to_state:
            loop_radius = 30
            t = np.linspace(0, 2 * np.pi, 100)

            center_x = x1
            center_y = y1 - loop_radius

            loop_x = center_x + loop_radius * np.cos(t)
            loop_y = center_y + loop_radius * np.sin(t)

            graph_widget.plot(loop_x, loop_y, pen=pg.mkPen('darkgray', width=2))

            angle_for_label = np.pi / 16
            label_x = center_x + loop_radius * np.cos(angle_for_label)
            label_y = center_y + loop_radius * np.sin(angle_for_label)

            label = pg.TextItem()
            label.setHtml(label_html)
            label.setAnchor((0.5, 0.5))
            label.setPos(label_x, label_y)
            graph_widget.addItem(label)

        else:
            control_x = (x1 + x2) / 2
            control_y = (y1 + y2) / 2 + curvature if from_state < to_state else (y1 + y2) / 2 - curvature
            t = np.linspace(0, 1, 100)
            curve_x = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * control_x + t ** 2 * x2
            curve_y = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * control_y + t ** 2 * y2

            graph_widget.plot(curve_x, curve_y, pen=pg.mkPen('darkgray', width=2))

            t_label = 0.25
            label_x = (1 - t_label) ** 2 * x1 + 2 * (1 - t_label) * t_label * control_x + t_label ** 2 * x2
            label_y = (1 - t_label) ** 2 * y1 + 2 * (1 - t_label) * t_label * control_y + t_label ** 2 * y2

            label = pg.TextItem()
            label.setHtml(label_html)
            label.setAnchor((0.5, 0.5))
            label.setPos(label_x, label_y)
            graph_widget.addItem(label)

    # Rysuj same wierzchołki, nawet jeśli nie mają przejść
    node_radius = 20
    for state_key, state_data in all_states:
        if state_key not in positions:
            positions[state_key] = (np.random.uniform(-1, 1) * scale, np.random.uniform(-1, 1) * scale)

        x, y = positions[state_key]
        
        state_assertion = state_data.get('state').assert_state()
        scatter = HoverScatterPlotItem([x], [y], 
                                     pen=None, 
                                     symbol='o', 
                                     size=node_radius * 2, 
                                     brush='lightblue',
                                     tooltip_text=f"State: {state_key}\nAssertion: {state_assertion}")
        
        graph_widget.addItem(scatter)
        
        text = pg.TextItem(str(state_key), anchor=(0.5, 0.5), color='black')
        text.setPos(x, y)
        graph_widget.addItem(text)
