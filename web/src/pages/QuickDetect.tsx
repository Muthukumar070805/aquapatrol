import { useMemo, useRef, useState } from 'react';
import { sampleSrc } from '../lib/api';
import type { Sample } from '../lib/types';
import { useSamples } from '../hooks/useSamples';
import { useYoloDetect } from '../hooks/useYoloDetect';
import { useYoloStatus } from '../hooks/useYoloStatus';

interface Selection {
  src: string;
  blob: Blob;
  filename: string;
}

export default function QuickDetect() {
  const samplesQuery = useSamples();
  const detect = useYoloDetect();
  const yoloQuery = useYoloStatus();

  const samples = samplesQuery.data?.samples || [];
  const yoloAvailable = yoloQuery.data?.available ?? null;

  const [activeSampleId, setActiveSampleId] = useState<string | null>(null);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const fileInput = useRef<HTMLInputElement>(null);
  const objectUrl = useRef<string | null>(null);

  function setUploadedFile(file: File) {
    if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
    const url = URL.createObjectURL(file);
    objectUrl.current = url;
    setActiveSampleId(null);
    detect.reset();
    setSelection({ src: url, blob: file, filename: file.name });
  }

  async function selectSample(s: Sample) {
    setActiveSampleId(s.id);
    detect.reset();
    const src = sampleSrc(s.url);
    try {
      const res = await fetch(src);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const filename = s.url.split('/').pop() || `${s.id}.png`;
      setSelection({ src, blob, filename });
    } catch (e) {
      console.error('Could not load sample:', e);
    }
  }

  function runDetect() {
    if (!selection) return;
    detect.mutate({ file: selection.blob, filename: selection.filename });
  }

  function downloadResult() {
    if (!detect.data) return;
    const a = document.createElement('a');
    a.href = detect.data.yolo_result_image;
    a.download = 'yolo-detections.png';
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  const canDetect = useMemo(
    () => !!selection && yoloAvailable !== false && !detect.isPending,
    [selection, yoloAvailable, detect.isPending]
  );

  const detections = detect.data?.detections ?? [];

  return (
    <section>
      <div className="view-head">
        <h1>Quick Detect</h1>
        <p>
          Run YOLO oil-candidate detection on a single image. Pick a built-in
          sample for an instant result, or drop in your own scene.
        </p>
      </div>

      <div className="detect-grid">
        <div className="panel">
          {yoloAvailable === false && (
            <div className="error-box" style={{ marginBottom: '1rem' }}>
              YOLO detector unavailable
              {yoloQuery.data?.detail ? `: ${yoloQuery.data.detail}` : '.'}
            </div>
          )}

          <div
            className={`dropzone${dragOver ? ' over' : ''}`}
            onClick={() => fileInput.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const f = e.dataTransfer.files?.[0];
              if (f) setUploadedFile(f);
            }}
            data-testid="dropzone"
          >
            <strong>Drop an image</strong>
            <div style={{ fontSize: '0.85rem', opacity: 0.7 }}>
              or click to browse
            </div>
            <input
              ref={fileInput}
              type="file"
              accept="image/*"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) setUploadedFile(f);
              }}
            />
          </div>

          {samples.length > 0 && (
            <>
              <div
                style={{ fontSize: '0.85rem', marginTop: '1rem', opacity: 0.7 }}
              >
                Or pick a sample
              </div>
              <div className="samples">
                {samples.map((s) => (
                  <button
                    key={s.id}
                    className={activeSampleId === s.id ? 'active' : ''}
                    onClick={() => selectSample(s)}
                    data-testid={`sample-${s.id}`}
                    title={s.id}
                  >
                    <img src={sampleSrc(s.url)} alt={s.id} loading="lazy" />
                  </button>
                ))}
              </div>
            </>
          )}

          <button
            className="primary"
            style={{ width: '100%', marginTop: '1rem' }}
            disabled={!canDetect}
            onClick={runDetect}
            data-testid="detect-btn"
          >
            {detect.isPending ? (
              <>
                <span className="spinner" /> Running YOLO detection...
              </>
            ) : (
              'Detect'
            )}
          </button>

          <div style={{ fontSize: '0.85rem', marginTop: '0.75rem', opacity: 0.8 }}>
            YOLO flags oil candidates for investigation — not confirmed spills.
          </div>

          {detect.isError && (
            <div className="error-box" style={{ marginTop: '1rem' }}>
              {detect.error instanceof Error ? detect.error.message : String(detect.error)}
            </div>
          )}
        </div>

        <div className="panel">
          {!selection ? (
            <p style={{ opacity: 0.7 }}>Select a sample image above or drop your own scene to begin detection.</p>
          ) : (
            <>
              <div className="compare">
                <figure>
                  <figcaption>Original</figcaption>
                  <div className="image-frame">
                    <img src={selection.src} alt="Original input" />
                  </div>
                </figure>
                <figure>
                  <figcaption>YOLO detections</figcaption>
                  <div className="image-frame">
                    {detect.data ? (
                      <img
                        src={detect.data.yolo_result_image}
                        alt="YOLO detections"
                        data-testid="yolo-result-img"
                      />
                    ) : (
                      <img src={selection.src} alt="Base" style={{ opacity: 0.4 }} />
                    )}
                  </div>
                </figure>
              </div>

              {detect.data && (
                <>
                  <div className="stat">
                    <span>Candidates</span>
                    <span className="val" data-testid="candidate-count">
                      {detect.data.num_candidates}
                    </span>
                  </div>

                  {detections.length > 0 && (
                    <div style={{ marginTop: '1rem', overflowX: 'auto' }}>
                      <table
                        style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: 'var(--font-size-meta)', fontFamily: 'var(--font-mono)' }}
                        data-testid="candidate-table"
                      >
                        <thead>
                          <tr>
                            <th style={{ borderBottom: '1px solid var(--border)', padding: '4px' }}>Spill ID</th>
                            <th style={{ borderBottom: '1px solid var(--border)', padding: '4px' }}>Conf</th>
                            <th style={{ borderBottom: '1px solid var(--border)', padding: '4px' }}>Box</th>
                          </tr>
                        </thead>
                        <tbody>
                          {detections.map((d) => (
                            <tr key={d.spill_id} data-testid="candidate-row">
                              <td style={{ borderBottom: '1px solid var(--border)', padding: '4px' }}>{d.spill_id}</td>
                              <td style={{ borderBottom: '1px solid var(--border)', padding: '4px' }}>
                                {Math.round(d.confidence * 100)}%
                              </td>
                              <td style={{ borderBottom: '1px solid var(--border)', padding: '4px' }}>
                                {d.bbox.join(', ')}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  <button
                    style={{ marginTop: '1rem' }}
                    onClick={downloadResult}
                    data-testid="download-result"
                  >
                    Download annotated (PNG)
                  </button>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
