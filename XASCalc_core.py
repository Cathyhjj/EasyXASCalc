import re
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import xraylib as xrl
import scipy.ndimage as nd
from IPython.display import display, HTML

# Enable LaTeX rendering for Plotly figures
import plotly
plotly.offline.init_notebook_mode()
display(HTML(
    '<script type="text/javascript" async src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.1/MathJax.js?config=TeX-MML-AM_SVG"></script>'
))

def formula_to_latex(formula: str) -> str:
    """
    Converts a chemical formula string (e.g., "CH2CF2") into a LaTeX-compatible string.
    
    Args:
    - formula (str): The chemical formula as a string.
    
    Returns:
    - str: The LaTeX-formatted chemical formula.
    """
    pattern = r'([A-Z][a-z]*)(\d*\.?\d*)'
    matches = re.findall(pattern, formula)
    
    latex_formula = ""
    for element, count in matches:
        if not count:  # If no number, assume it's '1'
            latex_formula += f"\\text{{{element}}}"
        else:
            latex_formula += f"\\text{{{element}}}_{{{count}}}"
    
    return latex_formula

def interpolate(img, zoom=3, order=1):
    """
    Interpolates a given image by a zoom factor and interpolation order.

    Parameters:
    - img: Input image to be interpolated.
    - zoom: Zoom factor for interpolation (default: 3).
    - order: Order of interpolation (default: 1).

    Returns:
    - Interpolated image.
    """
    return nd.zoom(img, zoom=zoom, order=order)

def select_data(xx, yy, data_lst, lower_threshold, upper_threshold, plot=False):
    """
    Selects data based on thresholds and applies a mask. Optionally plots the result.
    
    Parameters:
    - xx, yy: Grid data for plotting.
    - data_lst: List of data arrays to apply the thresholds.
    - lower_threshold, upper_threshold: Lists of lower and upper threshold values for masking.
    - plot: Boolean flag to show interactive plots (default False).
    
    Returns:
    - Mask array with selected data.
    """
    mask = np.ones_like(xx)
    
    for i, data in enumerate(data_lst):    
        masked_data = np.ma.masked_outside(data, lower_threshold[i], upper_threshold[i])
        mask_i = ~masked_data.mask
        mask *= mask_i
    
        if plot:
            fig = go.Figure(data=go.Heatmap(z=masked_data, x=xx, y=yy, colorscale="Blues"))
            fig.update_layout(title=f"Masked Data {i}")
    
    if plot:
        fig = go.Figure(data=go.Heatmap(z=mask, x=xx, y=yy, colorscale="Blues"))
        fig.update_layout(title="Final Mask", coloraxis_colorbar=dict(title="Mask"))

    return mask

def contour_plot(xx, yy, plot_data, title="", label="", cmap="Viridis", save=True, contour_line=True):
    """
    Plots a contour map using Plotly with optional contour lines.
    
    Parameters:
    - xx, yy: Grid data.
    - plot_data: Data to plot.
    - title: Plot title (default: empty).
    - label: Label for the colorbar (default: empty).
    - cmap: Colormap (default: 'Viridis').
    - save: Boolean to save the plot as an image (default: True).
    - contour_line: Boolean to add contour lines (default: True).
    """
    interp_xx, interp_yy, interp_data = map(lambda z: interpolate(z), [xx, yy, plot_data])
    
    fig = go.Figure(data=go.Heatmap(z=interp_data, x=interp_xx, y=interp_yy, colorscale=cmap, colorbar=dict(title=label)))
    
    if contour_line:
        fig.add_trace(go.Contour(z=interp_data, x=interp_xx, y=interp_yy, colorscale="Blues", showscale=False))
    
    fig.update_layout(title=title, xaxis_title="Active material [%]", yaxis_title="Area density [mg/cm²]")
    
    if save:
        fig.write_image(f"{title}.jpg")
    
def compound_generator(elements, composition, printit=False):
    """
    Generates a chemical formula from elements and their composition.
    
    Parameters:
    - elements: List of element symbols.
    - composition: List of element compositions (as integers or floats).
    - printit: Boolean to print the compound (default: False).
    
    Returns:
    - Compound formula as a string.
    """
    compound = ''.join(f"{el}{comp}" for el, comp in zip(elements, composition))
    if printit:
        print(compound)
    return compound

class MaterialAbs:
    def __init__(self, compounds_info, element, edge='K'):
        """
        Initializes a MaterialAbs object to compute absorption.

        Parameters:
        - compounds_info: List of compound info dictionaries (compound and area density).
        - element: The chemical symbol of the element (e.g., 'Mn').
        - edge: The absorption edge type ('K', 'L1', 'L2', 'L3').
        """
        self.compounds_info = compounds_info
        self.element = element
        self.edge = edge
        self.printlst = {}

        # Determine the atomic number of the element
        Z = xrl.SymbolToAtomicNumber(self.element)

        # Map the edge type to the corresponding xraylib shell constant
        edge_map = {
            "K": xrl.K_SHELL,
            "L1": xrl.L1_SHELL,
            "L2": xrl.L2_SHELL,
            "L3": xrl.L3_SHELL
        }

        if self.edge not in edge_map:
            raise ValueError(f"Invalid edge type: {self.edge}. Choose from 'K', 'L1', 'L2', or 'L3'.")

        # Get the edge energy in keV
        self.edge_value = xrl.EdgeEnergy(Z, edge_map[self.edge]) * 1000  # Convert to eV

        # Set up the energy range for the calculations
        self.energy = np.arange(max(100, self.edge_value - 500), self.edge_value + 500) / 1000  # in keV

    def edge_jump_calc(self, E1=None, E2=None):
        """
        Calculates the edge jump in absorption between two energy points.
        
        Parameters:
        - E1, E2: Lower and upper energy bounds (default: None).
        
        Returns:
        - Edge jump value.
        """
        mask = np.s_[:] if E1 is None else ~np.ma.masked_outside(self.energy * 1000, E1, E2).mask
        self.abs_max = self.abs_total[mask].max()
        self.abs_min = self.abs_total[mask].min()
        self.edge_jump = self.abs_max - self.abs_min
        self.printlst.update({
            "01_abs_max": f"Abs Max. is {self.abs_max:.3f}",
            "02_abs_min": f"Abs Min. is {self.abs_min:.3f}",
            "03_abs_edge_jump": f"Abs edge jump is {self.edge_jump:.3f}"
        })
        return self.edge_jump

    def abs_calc(self):
        """
        Calculates the total absorption for all compounds.
        
        Returns:
        - Total absorption as an array.
        """
        self.abs_total = np.zeros_like(self.energy)
        self.compound_name_all_latex = "$$"
        self.compound_name_all = ""

        for compound_info in self.compounds_info:
            compound = compound_info["compound"]
            area_density = compound_info["area_density"]

            # Use formula_to_latex to generate LaTeX formula from the compound string
            compound_latex = formula_to_latex(compound)
            
            # Calculate absorption
            compound_info["abs"] = np.array([xrl.CS_Total_CP(compound, E) * area_density for E in self.energy])
            self.abs_total += compound_info["abs"]

            # Append LaTeX-formatted compound to title strings
            self.compound_name_all_latex += f"{area_density * 1000:.1f}\\,\\frac{{mg}}{{cm^2}}\\, {compound_latex} + "
            self.compound_name_all += f"{area_density * 1000:.1f} mg/cm² {compound} + "

        # Remove the trailing " + " from the final string
        self.compound_name_all_latex = self.compound_name_all_latex.rstrip(" + ") + "$$"
        self.compound_name_all = self.compound_name_all.rstrip(" + ")

        # Store details in the print list
        self.printlst["00_compounds_info"] = "=" * 80 + f"\n {self.compound_name_all} \n" + "=" * 80
        
        # Calculate the edge jump
        E1 = self.edge_value - 50
        if E1 < 0:
            E1 = 100
        E2 = self.edge_value + 50
        self.edge_jump_calc(E1=E1, E2=E2)
        
        # Calculate the transmission
        self.transmitted_percentage = np.exp(-self.abs_total) * 100
        return self.abs_total

    def plot(self, plot_transmission=True, fontsize=14, show_label=True, width=800, height=500, abs_edge='', **kwargs):
        """
        Plots the absorption spectrum using plotly with customizable figure size and enhanced aesthetics.
        Adds a second y-axis to plot the transmission spectrum if requested and a table of key values below the plot.
        
        Parameters:
        - plot_transmission: Boolean to plot the transmission spectrum (default True).
        - fontsize: Font size for labels (default 14).
        - show_label: Boolean to show legend (default True).
        - width, height: Dimensions for the figure (default 900x600).
        """
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True,
            vertical_spacing=0.2,
            row_heights=[0.7, 0.3],
            specs=[[{"secondary_y": True}], [{"type": "table"}]]
        )

        # Absorption spectrum (primary y-axis)
        fig.add_trace(go.Scatter(
            x=self.energy * 1000, 
            y=self.abs_total, 
            mode='lines', 
            name='X-ray Absorption',  
            line=dict(width=4, color='rgba(0, 0, 128, 0.7)'),
            **kwargs
        ), row=1, col=1, secondary_y=False)

        if plot_transmission:
            fig.add_trace(go.Scatter(
                x=self.energy * 1000, 
                y=self.transmitted_percentage, 
                mode='lines', 
                name='X-ray Transmission',  
                line=dict(
                    width=1.5, 
                    color='rgba(128, 0, 128, 0.7)',  
                    dash='dashdot'
                ),  
                **kwargs
            ), row=1, col=1, secondary_y=True)

        # Prepare the values for the table        
        header = [f"<b style='color: blue;'>{self.element} {self.edge} ({self.edge_value:.1f} eV)</b>", "Value"]
        table_values = [
            ["Edge Jump (Δμx)", "Maximum Absorption (μx_max)"],
            [f"{self.edge_jump:.2f}", f"{self.abs_max:.2f}"]
        ]

        # Add table to the second row
        fig.add_trace(go.Table(
            header=dict(values=header, fill_color="lightgrey", align="center", font=dict(size=fontsize)),
            cells=dict(values=table_values, fill_color="white", align="center", font=dict(size=fontsize-2)),
            columnwidth=[1.5, 1]  
        ), row=2, col=1)

        # Customize layout with dual y-axes
        fig.update_layout(
            width=width,
            height=height,
            xaxis_title="Energy (eV)",
            title=self.compound_name_all_latex,
            title_font=dict(size=fontsize + 2),
            paper_bgcolor='white',
            plot_bgcolor='white',
            margin=dict(l=60, r=60, t=60, b=60),
            font=dict(family="Arial, sans-serif", size=fontsize),
            hovermode="x"
        )

        fig.update_yaxes(
            title_text="Absorption", 
            showgrid=True, 
            gridcolor='LightGray', 
            zeroline=False, 
            tickfont=dict(size=fontsize),
            range=[self.abs_min - 0.1, self.abs_max + 0.1],
            secondary_y=False
        )

        fig.update_yaxes(
            title_text="Transmission (%)", 
            showgrid=False, 
            tickfont=dict(size=fontsize),
            secondary_y=True
        )

        fig.update_xaxes(
            showgrid=True, 
            gridcolor='LightGray', 
            zeroline=False, 
            tickfont=dict(size=fontsize),
            range=[self.edge_value - 50, self.edge_value + 100]
        )

        if show_label:
            fig.update_layout(showlegend=True, legend=dict(
                x=1.1, y=1,
                bgcolor='rgba(255, 255, 255, 0.7)',
            ))
        
        return fig

    def type_writer(self, sort=True):
        """
        Prints the calculated absorption values in order.
        
        Parameters:
        - sort: Boolean to sort output keys (default: True).
        """
        sorted_printlst = sorted(self.printlst) if sort else self.printlst
        for item in sorted_printlst:
            print(self.printlst[item])

import ipywidgets as widgets
from IPython.display import display
import plotly.graph_objects as go
import plotly.io as pio  # Import plotly.io to manage renderers

class AbsorptionCalculator:
    def __init__(self, renderer="notebook"):
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