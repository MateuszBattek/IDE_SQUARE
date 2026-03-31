import pytest
import pyqtgraph as pg
from PyQt5 import QtWidgets
from components.fsm_components.graph_gen import draw_tree, draw_state_machine, HoverScatterPlotItem
import os

os.environ['QT_QPA_PLATFORM'] = 'offscreen'

@pytest.fixture
def app():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app

@pytest.fixture
def graph_widget(app):
    widget = pg.PlotWidget()
    yield widget
    widget.deleteLater()

@pytest.fixture
def sample_tree_data():
    edges = [
        ('root', 'child1'),
        ('root', 'child2'),
        ('child1', 'grandchild1'),
        ('child1', 'grandchild2'),
        ('child2', 'grandchild3')
    ]
    node_names = {
        'root': 'Root State',
        'child1': 'Child State 1',
        'child2': 'Child State 2',
        'grandchild1': 'Grandchild 1',
        'grandchild2': 'Grandchild 2',
        'grandchild3': 'Grandchild 3'
    }
    return edges, node_names

@pytest.fixture
def sample_state_machine_data():
    transitions = [
        ('state1', 'state2', 'event1'),
        ('state2', 'state3', 'event2'),
        ('state3', 'state1', 'event3'),
        ('state1', 'state1', 'loop_event')
    ]
    all_states = [
        ('state1', {'state': type('State', (), {'assert_state': lambda self: 'assertion1'})()}),
        ('state2', {'state': type('State', (), {'assert_state': lambda self: 'assertion2'})()}),
        ('state3', {'state': type('State', (), {'assert_state': lambda self: 'assertion3'})()})
    ]
    return transitions, all_states

def test_draw_tree(graph_widget, sample_tree_data):
    edges, node_names = sample_tree_data
    draw_tree(graph_widget, edges, node_names)
    
    items = list(graph_widget.items())
    
    edge_items = [item for item in items 
            if isinstance(item, pg.PlotDataItem) 
            and item.opts.get('pen') is not None 
            and item.opts.get('symbol') is None]
    assert len(edge_items) == 5, f"Expected 5 edges, got {len(edge_items)}"
    
    node_items = [item for item in items 
            if isinstance(item, pg.PlotDataItem) 
            and item.opts.get('symbol') is not None]
    assert len(node_items) == 6, f"Expected 6 nodes, got {len(node_items)}"

def test_draw_state_machine(graph_widget, sample_state_machine_data):
    transitions, all_states = sample_state_machine_data
    draw_state_machine(graph_widget, transitions, all_states)
    
    items = list(graph_widget.items())
    
    state_nodes = [item for item in items if isinstance(item, HoverScatterPlotItem)]
    assert len(state_nodes) == 3, f"Expected 3 states, got {len(state_nodes)}"
    
    edges = [item for item in items 
            if isinstance(item, pg.PlotDataItem)
            and item.opts.get('pen') is not None
            and item.opts.get('symbol') is None]
    assert len(edges) == 4, f"Expected 4 edges, got {len(edges)}"