import { useState, useEffect } from 'react'
import {
  Identity, TodayEntry, AlltimeEntry,
  getIdentity, claimUsername, fetchToday, fetchAlltime,
} from '../lib/leaderboard'

const USERNAME_RE = /^[A-Za-z0-9_-]{3,20}$/

interface LeaderboardModalProps {
  isOpen: boolean
  onClose: () => void
  onUsernameClaimed: (username: string) => void
  t: Record<string, any>
}

export function LeaderboardModal({ isOpen, onClose, onUsernameClaimed, t }: LeaderboardModalProps) {
  const [tab, setTab] = useState<'today' | 'alltime'>('today')
  const [today, setToday] = useState<TodayEntry[]>([])
  const [alltime, setAlltime] = useState<AlltimeEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [nameInput, setNameInput] = useState('')
  const [claiming, setClaiming] = useState(false)
  const [claimError, setClaimError] = useState(false)
  const [identity, setIdentity] = useState<Identity | null>(null)

  useEffect(() => {
    if (!isOpen) return
    setLoading(true)
    Promise.all([fetchToday(), fetchAlltime(), getIdentity()])
      .then(([td, at, id]) => { setToday(td); setAlltime(at); setIdentity(id) })
      .catch(() => { setToday([]); setAlltime([]) })
      .finally(() => setLoading(false))
  }, [isOpen])

  if (!isOpen) return null

  const handleClaim = async () => {
    if (!USERNAME_RE.test(nameInput) || claiming) return
    setClaiming(true)
    setClaimError(false)
    const result = await claimUsername(nameInput)
    setClaiming(false)
    if (result === 'ok') {
      setIdentity({ username: nameInput })
      onUsernameClaimed(nameInput)
    } else if (result === 'username_taken') {
      setClaimError(true)
    }
  }

  const rows = tab === 'today' ? today : alltime

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="card p-6 max-w-md w-full mx-4 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">🏆 {t.leaderboard}</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-900 dark:hover:text-white text-2xl leading-none">×</button>
        </div>

        {!identity && (
          <div className="mb-4 p-4 bg-blue-50 dark:bg-gray-700 rounded-lg">
            <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">{t.choose_username}</p>
            <div className="flex gap-2">
              <input
                type="text"
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleClaim()}
                placeholder={t.username_placeholder}
                maxLength={20}
                className="input-base flex-1"
              />
              <button
                onClick={handleClaim}
                disabled={!USERNAME_RE.test(nameInput) || claiming}
                className="btn-primary disabled:opacity-50"
              >
                {t.save}
              </button>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{t.username_rules}</p>
          </div>
        )}

        {claimError && (
          <div className="mb-4 p-3 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded-lg text-sm">
            {t.username_taken}
          </div>
        )}

        <div className="flex gap-2 mb-4">
          <button onClick={() => setTab('today')} className={tab === 'today' ? 'btn-primary flex-1' : 'btn-secondary flex-1'}>{t.today}</button>
          <button onClick={() => setTab('alltime')} className={tab === 'alltime' ? 'btn-primary flex-1' : 'btn-secondary flex-1'}>{t.all_time}</button>
        </div>

        <div className="overflow-y-auto flex-1">
          {loading ? (
            <p className="text-center text-gray-500 dark:text-gray-400 py-6">{t.loading}</p>
          ) : rows.length === 0 ? (
            <p className="text-center text-gray-500 dark:text-gray-400 py-6">{t.leaderboard_empty}</p>
          ) : (
            <table className="w-full text-sm">
              <tbody>
                {rows.map((entry, idx) => {
                  const isMe = identity && entry.username.toLowerCase() === identity.username.toLowerCase()
                  const medal = idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : `${idx + 1}.`
                  return (
                    <tr key={entry.username} className={`border-b border-gray-100 dark:border-gray-700 ${isMe ? 'bg-blue-50 dark:bg-gray-700 font-semibold' : ''}`}>
                      <td className="py-2 pr-2 w-10 text-gray-500 dark:text-gray-400">{medal}</td>
                      <td className="py-2 text-gray-900 dark:text-white">{entry.username}</td>
                      <td className="py-2 text-right text-gray-900 dark:text-white">
                        {tab === 'today' ? `${(entry as TodayEntry).score} ${t.points_abbr}` : `${(entry as AlltimeEntry).total_score} ${t.points_abbr}`}
                      </td>
                      <td className="py-2 pl-2 text-right text-gray-500 dark:text-gray-400 text-xs">
                        {tab === 'today'
                          ? ((entry as TodayEntry).won ? `✅ ${(entry as TodayEntry).guesses}/5 · 💡${(entry as TodayEntry).unlocks}` : '❌')
                          : `🏅 ${(entry as AlltimeEntry).wins}/${(entry as AlltimeEntry).games}`}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
