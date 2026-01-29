import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import axios from 'axios';
import { Plus, Trash2, Calculator, FlaskConical, Layers, Activity, Info, ThumbsUp } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import 'katex/dist/katex.min.css';
import { BlockMath } from 'react-katex';
import './App.css';

// Utility for generating unique IDs
const uid = () => Math.random().toString(36).substr(2, 9);

function App() {
  // State
  const [sample, setSample] = useState({
    compound: 'LiNi0.5Mn0.25Co0.25O2',
    area_density: 10,
    ratio: 0.2
  });

  const [matrices, setMatrices] = useState([
    { id: uid(), compound: 'BN', ratio: 0.8 }
  ]);
  const [components, setComponents] = useState([
    { id: uid(), compound: 'Al', area_density: 10 }
  ]);
  const [isCalculating, setIsCalculating] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);

  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);

  // Edge selection
  const [edges, setEdges] = useState([
    { id: uid(), type: 'K', element: 'Ni' },
    { id: uid(), type: 'K', element: 'Co' }
  ]);

  const [elementsList, setElementsList] = useState([]);

  // Fetch elements on mount
  useEffect(() => {
    axios.get('/api/elements')
      .then(res => setElementsList(res.data))
      .catch(err => console.error("Failed to fetch elements", err));
  }, []);

  // Update matrices ratios when sample ratio changes or matrices list changes
  useEffect(() => {
    const remainingRatio = 1 - sample.ratio;
    if (matrices.length > 0) {
      const perMatrix = remainingRatio / matrices.length;
      setMatrices(prev => prev.map(m => ({ ...m, ratio: perMatrix })));
    }
  }, [sample.ratio, matrices.length]);

  const addMatrix = () => {
    if (matrices.length < 1) {
      setMatrices(prev => [...prev, { id: uid(), compound: 'C', ratio: 0 }]);
    }
  };

  const removeMatrix = (id) => {
    setMatrices(prev => prev.filter(m => m.id !== id));
  };

  const addComponent = () => {
    setComponents(prev => [...prev, { id: uid(), compound: 'Al', area_density: 10 }]);
  };

  const removeComponent = (id) => {
    setComponents(prev => prev.filter(c => c.id !== id));
  };

  const addEdge = () => {
    setEdges(prev => [...prev, { id: uid(), type: 'K', element: 'Co' }]);
  };

  const removeEdge = (id) => {
    setEdges(prev => prev.filter(e => e.id !== id));
  };

  const handleLike = () => {
    if (!liked) {
      setLikeCount(prev => prev + 1);
      setLiked(true);
    } else {
      setLikeCount(prev => prev - 1);
      setLiked(false);
    }
  };

  const handleCalculate = async () => {
    setIsCalculating(true);
    setError(null);
    setResults([]);

    try {
      // Prepare payload
      // 1. Sample
      // density = input_density * ratio / 1000 (convert mg to g)
      const samplePayload = {
        compound: sample.compound,
        area_density: (sample.area_density / 1000) * sample.ratio
      };

      // 2. Matrices
      // density = sample_input_density * matrix_ratio / 1000
      const matricesPayload = matrices.map(m => ({
        compound: m.compound,
        area_density: (sample.area_density / 1000) * m.ratio
      }));

      // 3. Components
      // density = input_density / 1000
      const componentsPayload = components.map(c => ({
        compound: c.compound,
        area_density: c.area_density / 1000
      }));

      const allCompounds = [samplePayload, ...matricesPayload, ...componentsPayload];

      const edgesPayload = edges.map(e => ({
        element: e.element,
        edge_type: e.type
      }));

      const response = await axios.post('/api/calculate', {
        compounds: allCompounds,
        edges: edgesPayload
      });

      if (response.data.error) throw new Error(response.data.error);
      setResults(response.data.results);

    } catch (err) {
      setError(err.message || 'Calculation failed');
    } finally {
      setIsCalculating(false);
    }
  };

  // Auto-calculate on mount
  useEffect(() => {
    handleCalculate();
  }, []);

  return (
    <div className="app-container">
      <header className="header">
        <div className="logo">
          <FlaskConical className="icon" />
          <h1>EasyXASCalc <span className="beta">Web</span></h1>
        </div>
      </header>

      <main className="main-content">
        <div className="panels-grid">
          {/* Left Panel: Controls */}
          <div className="controls-panel">
            <button
              className="primary calculate-btn"
              onClick={handleCalculate}
              disabled={isCalculating}
            >
              {isCalculating ? 'Calculating...' : <><Calculator size={18} /> Calculate Absorption</>}
            </button>


            {/* Edges Section */}
            <section className="card highlight-card">
              <div className="section-header">
                <Activity size={18} />
                <h2>Measurement Edges</h2>
                <button className="icon-btn" onClick={addEdge}><Plus size={16} /></button>
              </div>

              <AnimatePresence>
                {edges.map((edge, idx) => (
                  <motion.div
                    key={edge.id}
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="row item-row"
                  >
                    <div style={{ flex: 1 }}>
                      <label className="label">Edge</label>
                      <select
                        value={edge.type}
                        onChange={e => {
                          const newE = [...edges];
                          newE[idx].type = e.target.value;
                          setEdges(newE);
                        }}
                      >
                        {['K', 'L1', 'L2', 'L3'].map(t => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </div>
                    <div style={{ flex: 2 }}>
                      <label className="label">Element</label>
                      <select
                        value={edge.element}
                        onChange={e => {
                          const newE = [...edges];
                          newE[idx].element = e.target.value;
                          setEdges(newE);
                        }}
                      >
                        {elementsList.length > 0 ? elementsList.map(el => (
                          <option key={el.atomic_number} value={el.symbol}>{el.symbol} (Z={el.atomic_number})</option>
                        )) : <option value={edge.element}>{edge.element}</option>}
                      </select>
                    </div>
                    <button className="danger icon-btn" onClick={() => removeEdge(edge.id)}>
                      <Trash2 size={16} />
                    </button>
                  </motion.div>
                ))}
              </AnimatePresence>
            </section>


            {/* Sample & Matrices Section */}
            <section className="card">
              <div className="section-header">
                <Layers size={18} />
                <h2>Sample & Matrices</h2>
              </div>
              <div className="grid">
                <div>
                  <label className="label">Compound Formula</label>
                  <input
                    type="text"
                    value={sample.compound}
                    onChange={e => setSample({ ...sample, compound: e.target.value })}
                  />
                </div>
                <div>
                  <label
                    className="label help-cursor"
                    data-tooltip="Mass per unit area. Example: A 10 mm diameter round pellet (area ≈ 0.79 cm²) weighing 100 mg has a density of 100 mg ÷ 0.79 cm² ≈ 127.3 mg/cm²."
                    style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                  >
                    Area Density (mg/cm²) <Info size={12} />
                  </label>
                  <input
                    type="number"
                    value={sample.area_density}
                    onChange={e => setSample({ ...sample, area_density: parseFloat(e.target.value) })}
                  />
                </div>
                <div>
                  <label className="label">Ratio: {sample.ratio.toFixed(2)} (Sample) / {(1 - sample.ratio).toFixed(2)} (Matrix)</label>
                  <input
                    type="range"
                    min="0.1" max="1.0" step="0.01"
                    value={sample.ratio}
                    onChange={e => setSample({ ...sample, ratio: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                </div>
              </div>
              {/* Matrices Subsection */}
              <div style={{ marginTop: '2rem', paddingTop: '1.5rem', borderTop: '1px dashed var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Layers size={16} className="text-muted" />
                    <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Matrix</h3>
                  </div>
                  <button className="icon-btn" onClick={addMatrix} disabled={matrices.length >= 1} style={{ opacity: matrices.length >= 1 ? 0.3 : 1 }}><Plus size={16} /></button>
                </div>

                <AnimatePresence>
                  {matrices.map((m, idx) => (
                    <motion.div
                      key={m.id}
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="row item-row"
                    >
                      <div style={{ flex: 2 }}>
                        <label className="label">Formula</label>
                        <input
                          type="text"
                          value={m.compound}
                          onChange={e => {
                            const newM = [...matrices];
                            newM[idx].compound = e.target.value;
                            setMatrices(newM);
                          }}
                        />
                      </div>
                      <div style={{ flex: 1 }}>
                        <label className="label">Ratio</label>
                        <div className="read-only-val">{m.ratio.toFixed(2)}</div>
                      </div>
                      <button className="danger icon-btn" onClick={() => removeMatrix(m.id)}>
                        <Trash2 size={16} />
                      </button>
                    </motion.div>
                  ))}
                </AnimatePresence>
                {matrices.length === 0 && <div className="empty-state">No matrix added</div>}
              </div>
            </section>

            {/* Components Section */}
            <section className="card">
              <div className="section-header">
                <Layers size={18} className="text-muted" />
                <h2>Extra Components</h2>
                <button className="icon-btn" onClick={addComponent}><Plus size={16} /></button>
              </div>

              <AnimatePresence>
                {components.map((c, idx) => (
                  <motion.div
                    key={c.id}
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="row item-row"
                  >
                    <div style={{ flex: 1, display: 'grid', gap: '0.8rem' }}>
                      <div>
                        <label className="label">Formula</label>
                        <input
                          type="text"
                          value={c.compound}
                          onChange={e => {
                            const newC = [...components];
                            newC[idx].compound = e.target.value;
                            setComponents(newC);
                          }}
                        />
                      </div>
                      <div>
                        <label
                          className="label help-cursor"
                          data-tooltip="Mass per unit area. Example: A 10 mm diameter round pellet (area ≈ 0.79 cm²) weighing 100 mg has a density of 100 mg ÷ 0.79 cm² ≈ 127.3 mg/cm²."
                          style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                        >
                          Area Density (mg/cm²) <Info size={12} />
                        </label>
                        <input
                          type="number"
                          value={c.area_density}
                          onChange={e => {
                            const newC = [...components];
                            newC[idx].area_density = parseFloat(e.target.value);
                            setComponents(newC);
                          }}
                        />
                      </div>
                    </div>
                    <button className="danger icon-btn" onClick={() => removeComponent(c.id)} style={{ alignSelf: 'flex-start', marginTop: '1.8rem' }}>
                      <Trash2 size={16} />
                    </button>
                  </motion.div>
                ))}
              </AnimatePresence>
              {components.length === 0 && <div className="empty-state">No extra components</div>}
            </section>





            {error && <div className="error-msg">{error}</div>}

          </div>

          {/* Right Panel: Results */}
          <div className="results-panel">
            {results.length === 0 && !isCalculating && (
              <div className="placeholder-state">
                <Activity size={48} className="text-muted" opacity={0.2} />
                <p>Configure composition and edges, then click Calculate.</p>
              </div>
            )}

            {results.map((res, idx) => (
              <motion.div
                key={idx}
                className="card plot-card"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1 }}
              >
                {res.error ? (
                  <div className="error-msg">Error: {res.error}</div>
                ) : (
                  <>
                    <h3>{res.element} - {res.edge} Edge ({res.edge_value?.toFixed(1)} eV)</h3>
                    {res.compound_latex && (
                      <div className="latex-container">
                        <BlockMath>{res.compound_latex.replace(/\$\$/g, '')}</BlockMath>
                      </div>
                    )}
                    <div className="stats-row">
                      <div className="stat" data-tooltip="The optimal edge jump is 1.0, with a recommended range of 0.3 to 3.0.">
                        <span className="label help-cursor" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          Edge Jump <Info size={12} />
                        </span>
                        <span className="value">{res.edge_jump?.toFixed(3)}</span>
                      </div>
                      <div className="stat" data-tooltip="Total absorption should ideally be kept below 4.0.">
                        <span className="label help-cursor" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          Max Absorption <Info size={12} />
                        </span>
                        <span className="value">{res.abs_max?.toFixed(3)}</span>
                      </div>
                    </div>
                    <div className="plot-container">
                      <Plot
                        data={res.plot.data}
                        layout={{
                          ...res.plot.layout,
                          width: undefined, // Let it be responsive
                          height: 350,
                          paper_bgcolor: '#ffffff',
                          plot_bgcolor: '#ffffff',
                          font: { color: '#1e293b' },
                          xaxis: { ...res.plot.layout.xaxis, gridcolor: '#e2e8f0', color: '#64748b' },
                          yaxis: { ...res.plot.layout.yaxis, gridcolor: '#e2e8f0', color: '#64748b' },
                          yaxis2: { ...res.plot.layout.yaxis2, gridcolor: '#e2e8f0', color: '#64748b' },
                          legend: { ...res.plot.layout.legend, bgcolor: 'rgba(255,255,255,0.7)' }
                        }}
                        config={{ responsive: true }}
                        style={{ width: '100%', height: '100%' }}
                      />
                    </div>
                  </>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </main>

      <footer className="footer">
        <div className="footer-content">
          <span>Developed by <a href="https://juanjuanhuang-cathy.github.io/" target="_blank" rel="noopener noreferrer">Juanjuan Huang</a> with the assistance of Gemini</span>

          <div className="divider" />

          <div className="like-section">
            <span>Give me a thumbs up if you found this useful!</span>
            <button
              className={clsx("like-btn", { liked })}
              onClick={handleLike}
              aria-label="Like"
            >
              <ThumbsUp size={18} fill={liked ? "currentColor" : "none"} />
            </button>
            <span className="like-count" key={likeCount}>{likeCount}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
