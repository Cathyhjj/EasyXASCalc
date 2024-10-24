import numpy as np
import ipywidgets as widgets
from IPython.display import display
import plotly.graph_objects as go
import xraylib as xrl
from .XASCalc_core import MaterialAbs
import plotly.io as pio  # Necessary for Colab renderer


class AbsorptionCalculator:
    def __init__(self, renderer="colab"):
        self.renderer = renderer  # Store the renderer

        # Add a label for the component
        self.label_sample = widgets.Label(value="Sample compositions")

        # Primary component (sample) input with area density and ratio
        self.compound_input = widgets.Text(value='LiNi0.5Mn0.25Co0.25O2', description='Sample:')
        self.compound_area_density_input = widgets.FloatText(
            value=10,
            description='Area density [mg/cm^2]:',
            layout=widgets.Layout(width='300px'),
            style={'description_width': '180px'}
        )

        self.compound_ratio_slider = widgets.FloatSlider(value=1.0, min=0.1, max=1.0, step=0.01, description='Ratio:')
        self.compound_box = widgets.HBox([self.compound_input, self.compound_ratio_slider, self.compound_area_density_input])

        # Matrices will be added here
        self.matrix_widgets = []
        self.matrices_box = widgets.VBox([])

        # Components will be added here
        self.component_widgets = []
        self.components_box = widgets.VBox([])

        # Button to add matrix inputs
        self.add_matrix_button = widgets.Button(description="Add a matrix")
        self.add_matrix_button.on_click(self.add_matrix)

        # Button to add component inputs
        self.add_component_button = widgets.Button(description="Add a component")
        self.add_component_button.on_click(self.add_component)

        # Add a label for the measurement
        self.label_measurement = widgets.Label(value="XAS measurement energies")

        # Dropdown for K-edge absorption and Edge type
        self.edge_type_dropdown = self.create_edge_type_dropdown()
        self.abs_edge_dropdown = self.create_abs_edge_dropdown(xrl.K_SHELL)

        # Put both dropdowns into a horizontal layout
        self.edge_selection_box = widgets.HBox([self.edge_type_dropdown, self.abs_edge_dropdown])

        # Button to trigger the calculation and plotting
        self.run_button = widgets.Button(description="Calculate")
        self.run_button.on_click(self.run_calculation)

        # Create an output region specifically for the plot
        self.plot_output = widgets.Output()

    def create_edge_type_dropdown(self):
        edge_types = [('K', xrl.K_SHELL), ('L1', xrl.L1_SHELL),
                      ('L2', xrl.L2_SHELL), ('L3', xrl.L3_SHELL)]

        dropdown = widgets.Dropdown(
            options=edge_types,
            description='Edge Type:'
        )

        # Add an event handler to update the element dropdown when the edge type changes
        dropdown.observe(self.on_edge_type_change, names='value')

        return dropdown

    def create_abs_edge_dropdown(self, shell):
        elements = [(xrl.AtomicNumberToSymbol(Z), Z) for Z in range(1, 101)]
        options = []
        for symbol, Z in elements:
            try:
                edge_energy = xrl.EdgeEnergy(Z, shell) * 1000
                options.append((f'{symbol} ({edge_energy:.1f} eV)', Z))
            except ValueError:
                pass

        return widgets.Dropdown(
            options=options,
            description='Element:'
        )

    def on_edge_type_change(self, change):
        new_shell = change['new']
        self.abs_edge_dropdown = self.create_abs_edge_dropdown(new_shell)
        self.edge_selection_box.children = [self.edge_type_dropdown, self.abs_edge_dropdown]

    def add_matrix(self, b):
        compound_ratio = self.compound_ratio_slider.value
        remaining_ratio = 1 - compound_ratio
        num_matrices = len(self.matrix_widgets) + 1

        for widget_group in self.matrix_widgets:
            widget_group['ratio_slider'].value = remaining_ratio / num_matrices

        new_matrix_ratio = remaining_ratio / num_matrices

        new_matrix_input = widgets.Text(value="C", description='Matrix:')
        new_matrix_ratio_slider = widgets.FloatSlider(value=new_matrix_ratio, min=0.0, max=1.0, step=0.01, description='Ratio:')
        remove_button = widgets.Button(description="Remove")

        def remove_matrix(b, matrix_box, widget_group):
            self.matrices_box.children = [child for child in self.matrices_box.children if child != matrix_box]
            self.matrix_widgets.remove(widget_group)
            self.update_ratios()

        remove_button.on_click(lambda b: remove_matrix(b, new_matrix_box, widget_group))

        new_matrix_box = widgets.HBox([new_matrix_input, new_matrix_ratio_slider, remove_button])

        widget_group = {
            'input': new_matrix_input,
            'ratio_slider': new_matrix_ratio_slider,
            'remove_button': remove_button,
            'box': new_matrix_box
        }

        self.matrix_widgets.append(widget_group)
        self.matrices_box.children = list(self.matrices_box.children) + [new_matrix_box]

    def add_component(self, b):
        new_component_input = widgets.Text(value="Al", description='Component:')
        new_component_area_density_input = widgets.FloatText(
            value=10,
            description='Area density [mg/cm^2]:',
            layout=widgets.Layout(width='250px'),
            style={'description_width': '180px'}
        )
        remove_button = widgets.Button(description="Remove")

        def remove_component(b, component_box, widget_group):
            self.components_box.children = [child for child in self.components_box.children if child != component_box]
            self.component_widgets.remove(widget_group)

        remove_button.on_click(lambda b: remove_component(b, new_component_box, widget_group))

        new_component_box = widgets.HBox([new_component_input, new_component_area_density_input, remove_button])

        widget_group = {
            'input': new_component_input,
            'area_density': new_component_area_density_input,
            'remove_button': remove_button,
            'box': new_component_box
        }

        self.component_widgets.append(widget_group)
        self.components_box.children = list(self.components_box.children) + [new_component_box]

    def update_ratios(self):
        compound_ratio = self.compound_ratio_slider.value
        remaining_ratio = 1 - compound_ratio
        num_matrices = len(self.matrix_widgets)

        if num_matrices > 0:
            for widget_group in self.matrix_widgets:
                widget_group['ratio_slider'].value = remaining_ratio / num_matrices

    def run_calculation(self, b):
        self.plot_output.clear_output(wait=True)

        with self.plot_output:
            formula = self.compound_input.value
            compound_area_density = self.compound_area_density_input.value / 1000
            compound_ratio = self.compound_ratio_slider.value

            Z = self.abs_edge_dropdown.value
            edge_type = self.edge_type_dropdown.label

            material_info_i = {
                "compound": formula,
                "area_density": compound_area_density * compound_ratio
            }

            matrix_info_list = []
            for widget_group in self.matrix_widgets:
                matrix_info = {
                    "compound": widget_group['input'].value,
                    "area_density": compound_area_density * widget_group['ratio_slider'].value
                }
                matrix_info_list.append(matrix_info)

            component_info_list = []
            for widget_group in self.component_widgets:
                component_info = {
                    "compound": widget_group['input'].value,
                    "area_density": widget_group['area_density'].value / 1000
                }
                component_info_list.append(component_info)

            all_components = [material_info_i] + matrix_info_list + component_info_list
            test = MaterialAbs(all_components, element=xrl.AtomicNumberToSymbol(Z), edge=edge_type)

            test.element = self.abs_edge_dropdown.label.split()[0]
            test.edge = self.edge_type_dropdown.label
            test.abs_calc()

            fig = test.plot(abs_edge=f'{test.element} {test.edge}')

            # Use direct display for Colab instead of fig.show()
            if self.renderer == "colab":
                pio.renderers.default = "colab"
                display(fig)
            else:
                fig.show(renderer=self.renderer)

    def display(self):
        display(widgets.VBox([self.label_sample,
                              self.compound_box,
                              self.matrices_box,
                              self.add_matrix_button,
                              self.components_box,
                              self.add_component_button,
                              self.label_measurement,
                              self.edge_selection_box,
                              self.run_button,
                              self.plot_output]))
