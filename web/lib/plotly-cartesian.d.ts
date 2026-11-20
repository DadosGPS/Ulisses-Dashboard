// Tipos dos pacotes de Plotly sem declarações próprias.
declare module "plotly.js-cartesian-dist-min" {
  import Plotly from "plotly.js";
  export default Plotly;
}
declare module "react-plotly.js/factory" {
  import type { ComponentType } from "react";
  import type { PlotParams } from "react-plotly.js";
  export default function createPlotlyComponent(plotly: unknown): ComponentType<PlotParams>;
}
