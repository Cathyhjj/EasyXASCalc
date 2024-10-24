
from XASCalc_core import MaterialAbs
import xraylib as xrl
import ipywidgets as widgets
from IPython.display import display
import plotly.graph_objects as go
import plotly.io as pio  # Import plotly.io to manage renderers

class AbsorptionCalculator:
    def __init__(self, renderer="plotly_mimetype") :
        # Store the selected renderer as an instance variable
        self.renderer = renderer
        
        # Add a label for the component
        self.label_sample = widgets.Label(value="Sample compositions")
        
        # Primary component (sample) input with area density and ratio
        self.compound_input = widgets.Text(value='LiNi0.5Mn0.25Co0.25O2', description='Sample:')
        self.compound_area_density_input = widgets.FloatText(
            value=10, 
            description='Area density [mg/cm^2]:',
            layout=widgets.Layout(width='300px'),  # Adjust width of the input box
            style={'description_width': '180px'}  # Adjust width of the label
        )
        
        self.compound_ratio_slider = widgets.FloatSlider(value=1.0, min=0.1, max=1.0, step=0.01, description='Ratio:')
        self.compound_box = widgets.HBox([self.compound_input, self.compound_ratio_slider, self.compound_area_density_input])

        # Matrices will be added here
        self.matrix_widgets = []  # Store matrix widgets (input, ratio slider, remove button)
        self.matrices_box = widgets.VBox([])

        # Components will be added here
        self.component_widgets = []  # Store component widgets (input, area density, remove button)
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
        self.abs_edge_dropdown = self.create_abs_edge_dropdown(xrl.K_SHELL)  # Initially set to K-edge

        # Put both dropdowns into a horizontal layout
        self.edge_selection_box = widgets.HBox([self.edge_type_dropdown, self.abs_edge_dropdown])

        # Button to trigger the calculation and plotting
        self.run_button = widgets.Button(description="Calculate")
        self.run_button.on_click(self.run_calculation)

        # Create two output regions: one for the plot and one for other outputs
        self.plot_output = widgets.Output()  # Output specifically for the plot
        self.output = widgets.Output()  # General output for other messages or results

        # Attach observer to update matrix ratios when the primary component ratio slider changes
        self.compound_ratio_slider.observe(self.on_ratio_change, names='value')

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
        elements = [(xrl.AtomicNumberToSymbol(Z), Z) for Z in range(1, 101)]  # Including elements with atomic numbers 1 to 100
        options = []
        for symbol, Z in elements:
            try:
                edge_energy = xrl.EdgeEnergy(Z, shell) * 1000  # Get edge energy in eV for the selected shell
                options.append((f'{symbol} ({edge_energy:.1f} eV)', Z))
            except ValueError:
                pass  # Ignore elements where the edge energy is not available
        
        return widgets.Dropdown(
            options=options,
            description='Element:'
        )

    def on_edge_type_change(self, change):
        # When the edge type dropdown is changed, update the element energies
        new_shell = change['new']  # Directly get the shell type (it's already an int)
        
        # Create a new abs_edge_dropdown with updated energies for the selected shell
        self.abs_edge_dropdown = self.create_abs_edge_dropdown(new_shell)
        
        # Update the display with the new dropdown
        self.edge_selection_box.children = [self.edge_type_dropdown, self.abs_edge_dropdown]

    def add_matrix(self, b):
        # Calculate the remaining ratio for all matrices
        compound_ratio = self.compound_ratio_slider.value
        remaining_ratio = 1 - compound_ratio
        num_matrices = len(self.matrix_widgets) + 1  # +1 because we are adding one new matrix
        
        # Update the ratio for existing matrices
        for widget_group in self.matrix_widgets:
            widget_group['ratio_slider'].value = remaining_ratio / num_matrices
        
        # Set the ratio for the new matrix
        new_matrix_ratio = remaining_ratio / num_matrices

        # Create new matrix input, ratio slider, and remove button
        new_matrix_input = widgets.Text(value="C", description='Matrix:')
        new_matrix_ratio_slider = widgets.FloatSlider(value=new_matrix_ratio, min=0.0, max=1.0, step=0.01, description='Ratio:')
        remove_button = widgets.Button(description="Remove")
        
        # Create a remove function for the matrix
        def remove_matrix(b, matrix_box, widget_group):
            self.matrices_box.children = [child for child in self.matrices_box.children if child != matrix_box]
            self.matrix_widgets.remove(widget_group)
            self.update_ratios()

        # Pass the widget group and matrix box correctly in the lambda
        remove_button.on_click(lambda b: remove_matrix(b, new_matrix_box, widget_group))

        # Combine these inputs in a horizontal layout
        new_matrix_box = widgets.HBox([new_matrix_input, new_matrix_ratio_slider, remove_button])

        # Store the inputs for later access in a dictionary
        widget_group = {
            'input': new_matrix_input,
            'ratio_slider': new_matrix_ratio_slider,
            'remove_button': remove_button,
            'box': new_matrix_box
        }

        # Add to the list of matrices
        self.matrix_widgets.append(widget_group)

        # Add the new layout to the vertical box of matrices
        self.matrices_box.children = list(self.matrices_box.children) + [new_matrix_box]

    def add_component(self, b):
        # Create new component input, area density input, and remove button
        new_component_input = widgets.Text(value="Al", description='Component:')
        new_component_area_density_input = widgets.FloatText(
            value=10, 
            description='Area density [mg/cm^2]:',
            layout=widgets.Layout(width='250px'),  # Adjust width of the input box
            style={'description_width': '180px'}  # Adjust width of the label
        )
        remove_button = widgets.Button(description="Remove")
        
        # Create a remove function for the component
        def remove_component(b, component_box, widget_group):
            self.components_box.children = [child for child in self.components_box.children if child != component_box]
            self.component_widgets.remove(widget_group)

        # Pass the widget group and component box correctly in the lambda
        remove_button.on_click(lambda b: remove_component(b, new_component_box, widget_group))

        # Combine these inputs in a horizontal layout
        new_component_box = widgets.HBox([new_component_input, new_component_area_density_input, remove_button])

        # Store the inputs for later access in a dictionary
        widget_group = {
            'input': new_component_input,
            'area_density': new_component_area_density_input,
            'remove_button': remove_button,
            'box': new_component_box
        }

        # Add to the list of components
        self.component_widgets.append(widget_group)

        # Add the new layout to the vertical box of components
        self.components_box.children = list(self.components_box.children) + [new_component_box]

    def update_ratios(self):
        """Updates the ratio sliders based on the current number of matrices."""
        compound_ratio = self.compound_ratio_slider.value
        remaining_ratio = 1 - compound_ratio
        num_matrices = len(self.matrix_widgets)
        
        if num_matrices > 0:
            for widget_group in self.matrix_widgets:
                widget_group['ratio_slider'].value = remaining_ratio / num_matrices

    def on_ratio_change(self, change):
        """Adjusts matrix ratios when the primary component ratio slider changes."""
        self.update_ratios()

    def run_calculation(self, b):
        # Clear and reinitialize the plot-specific output widget to ensure no stacking of figures
        self.plot_output.clear_output(wait=True)

        # Use the plot output region for the plot only
        with self.plot_output:
            # Get the primary component (sample) info
            formula = self.compound_input.value
            compound_area_density = self.compound_area_density_input.value / 1000
            compound_ratio = self.compound_ratio_slider.value

            # Get the selected element and edge type
            Z = self.abs_edge_dropdown.value  # Atomic number from the element dropdown
            edge_type = self.edge_type_dropdown.label  # Edge type (K, L1, L2, L3)

            # Primary sample info
            material_info_i = {
                "compound": formula,
                "area_density": compound_area_density * compound_ratio
            }

            # Gather all matrix information (area density same as sample)
            matrix_info_list = []
            for widget_group in self.matrix_widgets:
                matrix_info = {
                    "compound": widget_group['input'].value,
                    "area_density": compound_area_density * widget_group['ratio_slider'].value
                }
                matrix_info_list.append(matrix_info)

            # Gather all component information
            component_info_list = []
            for widget_group in self.component_widgets:
                component_info = {
                    "compound": widget_group['input'].value,
                    "area_density": widget_group['area_density'].value / 1000  # Convert to g/cm²
                }
                component_info_list.append(component_info)

            # Combine all components
            all_components = [material_info_i] + matrix_info_list + component_info_list
            test = MaterialAbs(all_components, 
                               element=xrl.AtomicNumberToSymbol(Z), 
                               edge=edge_type)

            # Pass element and edge information for display in the table
            test.element = self.abs_edge_dropdown.label.split()[0]
            test.edge = self.edge_type_dropdown.label
            test.abs_calc()

            # Generate the plot and display it using the specified renderer
            fig = test.plot(abs_edge=f'{test.element} {test.edge}')
            fig.show(renderer=self.renderer)  # Use the renderer passed to the constructor

    def display(self):
        # Show everything, including the plot output widget
        display(widgets.VBox([self.label_sample,
                              self.compound_box, 
                              self.matrices_box, 
                              self.add_matrix_button,
                              self.components_box, 
                              self.add_component_button,
                              self.label_measurement,
                              self.edge_selection_box, 
                              self.run_button, 
                              self.plot_output, 
                              self.output]))