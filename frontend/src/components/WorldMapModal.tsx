import { useState, useMemo, useRef } from 'react'
import { ComposableMap, Geographies, Geography, ZoomableGroup } from 'react-simple-maps'
// Heavy (~740KB) topology data: this whole module is loaded via React.lazy
// at the call site, so it never enters the main bundle for players who
// don't use Easy Mode.
import atlas from 'world-atlas/countries-50m.json'
import iso2ToMapId from '../assets/iso2-to-map-id.json'
import { CountryOption } from '../lib/api'

export type MarkState = 'neutral' | 'consider' | 'discard'

interface WorldMapModalProps {
  isOpen: boolean
  onClose: () => void
  marks: Record<string, MarkState>
  onMark: (iso2: string, mode: MarkState) => void
  countries: CountryOption[]
  t: Record<string, any>
}

// Reverse of the iso2 -> numeric-id crosswalk generated at build time
// (see frontend/src/assets/iso2-to-map-id.json) so a clicked map region
// (numeric id) resolves back to our own country records (iso2-keyed).
const mapIdToIso2: Record<string, string> = Object.fromEntries(
  Object.entries(iso2ToMapId as Record<string, string>).map(([iso2, id]) => [id, iso2])
)

// A few large landmasses on the map are dependent territories with their
// own geometry but aren't separately guessable in our country list - our
// game models them as part of their sovereign state, so clicking them
// should mark that state instead of being dead, confusing space.
// Greenland (id 304) -> Denmark (our Q756617 entity covers the whole
// Kingdom of Denmark, Greenland included). The Faroe Islands aren't
// rendered at all at this map resolution (too small), so no entry needed.
mapIdToIso2['304'] = 'DK'

const COLORS = {
  neutral: '#d1d5db', // gray-300
  consider: '#22c55e', // green-500
  discard: '#ef4444', // red-500
  noData: '#e5e7eb', // gray-200: landmass with no matching country (e.g. Antarctica)
}

const MODES: MarkState[] = ['consider', 'discard', 'neutral']

/** Easy Mode scratchpad: a world map where the player picks a mode
 * (consider / discard / unmark) and then clicks countries to apply it -
 * a bulk-marking tool, not a click-to-cycle toggle. Purely a note-taking
 * aid: it never submits a guess. The actual guess still goes through the
 * text input, as always. */
export function WorldMapModal({ isOpen, onClose, marks, onMark, countries, t }: WorldMapModalProps) {
  const [hovered, setHovered] = useState<string | null>(null)
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null)
  const [activeMode, setActiveMode] = useState<MarkState>('consider')
  const mapContainerRef = useRef<HTMLDivElement>(null)

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = mapContainerRef.current?.getBoundingClientRect()
    if (!rect) return
    setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top })
  }

  const nameByIso2 = useMemo(() => {
    const map: Record<string, string> = {}
    for (const c of countries) map[c.iso2] = c.name
    return map
  }, [countries])

  if (!isOpen) return null

  const fillFor = (iso2: string | undefined) => {
    if (!iso2) return COLORS.noData
    return COLORS[marks[iso2] ?? 'neutral']
  }

  const modeLabel: Record<MarkState, string> = {
    consider: t.map_mode_consider,
    discard: t.map_mode_discard,
    neutral: t.map_mode_clear,
  }
  const modeColor: Record<MarkState, string> = {
    consider: COLORS.consider,
    discard: COLORS.discard,
    neutral: COLORS.neutral,
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="card p-4 max-w-3xl w-full">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">🗺️ {t.map_title}</h2>
          <button
            onClick={onClose}
            className="text-2xl leading-none text-gray-500 hover:text-gray-900 dark:hover:text-white"
            aria-label={t.close}
          >
            ×
          </button>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">{t.map_instructions}</p>

        <div className="flex gap-2 mb-3">
          {MODES.map((mode) => (
            <button
              key={mode}
              onClick={() => setActiveMode(mode)}
              className="flex-1 px-3 py-2 rounded-lg text-sm font-medium border-2 transition-all"
              style={
                activeMode === mode
                  ? { background: modeColor[mode], borderColor: modeColor[mode], color: mode === 'neutral' ? '#1f2937' : '#fff' }
                  : { background: 'transparent', borderColor: modeColor[mode], color: modeColor[mode] }
              }
            >
              {modeLabel[mode]}
            </button>
          ))}
        </div>

        <div
          ref={mapContainerRef}
          onMouseMove={handleMouseMove}
          className="rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 relative bg-blue-50 dark:bg-gray-900"
          style={{ height: '55vh' }}
        >
          {hovered && mousePos && (
            <div
              className="absolute z-10 px-2 py-1 rounded bg-white/90 dark:bg-gray-800/90 text-sm font-medium text-gray-900 dark:text-white shadow pointer-events-none whitespace-nowrap"
              style={{
                left: mousePos.x,
                top: mousePos.y,
                transform: `translate(${
                  mousePos.x > (mapContainerRef.current?.clientWidth ?? 0) / 2 ? 'calc(-100% - 12px)' : '12px'
                }, -50%)`,
              }}
            >
              {hovered}
            </div>
          )}
          <ComposableMap projection="geoMercator" width={800} height={450} style={{ width: '100%', height: '100%' }}>
            <ZoomableGroup center={[10, 15]} zoom={1} minZoom={1} maxZoom={8}>
              <Geographies geography={atlas}>
                {({ geographies }) =>
                  geographies.map((geo) => {
                    const iso2 = mapIdToIso2[geo.id]
                    const name = iso2 ? nameByIso2[iso2] : undefined
                    return (
                      <Geography
                        key={geo.rsmKey}
                        id={iso2 ? `country-${iso2}-${geo.id}` : undefined}
                        geography={geo}
                        onClick={() => iso2 && onMark(iso2, activeMode)}
                        onMouseEnter={() => setHovered(name ?? null)}
                        onMouseLeave={() => setHovered(null)}
                        style={{
                          // No color change on hover/press - only a
                          // thicker stroke, so nothing ever "paints blue"
                          // before the player actually clicks.
                          default: {
                            fill: fillFor(iso2),
                            stroke: '#FFFFFF',
                            strokeWidth: 0.3,
                            outline: 'none',
                            cursor: iso2 ? 'pointer' : 'default',
                          },
                          hover: {
                            fill: fillFor(iso2),
                            stroke: iso2 ? '#1f2937' : '#FFFFFF',
                            strokeWidth: iso2 ? 1.2 : 0.3,
                            outline: 'none',
                          },
                          pressed: {
                            fill: fillFor(iso2),
                            stroke: '#1f2937',
                            strokeWidth: 1.5,
                            outline: 'none',
                          },
                        }}
                      />
                    )
                  })
                }
              </Geographies>
            </ZoomableGroup>
          </ComposableMap>
        </div>

        <button onClick={onClose} className="btn-primary w-full mt-3">
          {t.close}
        </button>
      </div>
    </div>
  )
}
