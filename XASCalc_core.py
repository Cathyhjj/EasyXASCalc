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
