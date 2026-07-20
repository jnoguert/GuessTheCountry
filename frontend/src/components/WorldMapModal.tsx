import { useState, useMemo } from 'react'
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
  onToggleMark: (iso2: string) => void
  countries: CountryOption[]
  t: Record<string, any>
}

// Reverse of the iso2 -> numeric-id crosswalk generated at build time
// (see frontend/src/assets/iso2-to-map-id.json) so a clicked map region
// (numeric id) resolves back to our own country records (iso2-keyed).
const mapIdToIso2: Record<string, string> = Object.fromEntries(
  Object.entries(iso2ToMapId as Record<string, string>).map(([iso2, id]) => [id, iso2])
)

const COLORS = {
  neutral: '#d1d5db', // gray-300
  consider: '#22c55e', // green-500
  discard: '#ef4444', // red-500
  hover: '#3b82f6', // blue-500
  pressed: '#2563eb', // blue-600
  noData: '#e5e7eb', // gray-200: landmass with no matching country (e.g. Antarctica)
}

/** Easy Mode scratchpad: a world map where the player marks countries as
 * "considering" or "discarded" while reasoning about the clue. Purely a
 * visual note-taking aid - it never submits a guess. The actual guess
 * still goes through the text input, as always. */
export function WorldMapModal({ isOpen, onClose, marks, onToggleMark, countries, t }: WorldMapModalProps) {
  const [hovered, setHovered] = useState<string | null>(null)

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
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{t.map_instructions}</p>

        <div className="flex gap-4 mb-2 text-xs text-gray-700 dark:text-gray-300">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-sm" style={{ background: COLORS.neutral }} />
            {t.map_neutral}
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-sm" style={{ background: COLORS.consider }} />
            {t.map_considering}
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-sm" style={{ background: COLORS.discard }} />
            {t.map_discarded}
          </span>
        </div>

        <div
          className="rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 relative bg-blue-50 dark:bg-gray-900"
          style={{ height: '55vh' }}
        >
          {hovered && (
            <div className="absolute top-2 left-2 z-10 px-2 py-1 rounded bg-white/90 dark:bg-gray-800/90 text-sm font-medium text-gray-900 dark:text-white shadow pointer-events-none">
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
                        geography={geo}
                        onClick={() => iso2 && onToggleMark(iso2)}
                        onMouseEnter={() => setHovered(name ?? null)}
                        onMouseLeave={() => setHovered(null)}
                        style={{
                          default: {
                            fill: fillFor(iso2),
                            stroke: '#FFFFFF',
                            strokeWidth: 0.3,
                            outline: 'none',
                            cursor: iso2 ? 'pointer' : 'default',
                          },
                          hover: {
                            fill: iso2 ? COLORS.hover : fillFor(iso2),
                            stroke: '#FFFFFF',
                            strokeWidth: 0.3,
                            outline: 'none',
                          },
                          pressed: {
                            fill: COLORS.pressed,
                            stroke: '#FFFFFF',
                            strokeWidth: 0.3,
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
