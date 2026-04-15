import { NavLink, Outlet } from 'react-router-dom'
import { roleAccess } from '../../data/mockData'
import { useSoc } from '../../context/SocContext'

const navItems = [
  { label: 'SOC Overview', to: '/' },
  { label: 'UEBA Analysis', to: '/operations' },
  { label: 'Reporting', to: '/reporting' },
]

export function AppLayout() {
  const {
    searchTerm,
    setSearchTerm,
    selectedRole,
    setSelectedRole,
    toast,
    dismissToast,
  } = useSoc()

  return (
    <div className="relative min-h-screen pb-10 text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(83,130,212,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(83,130,212,0.08)_1px,transparent_1px)] bg-[size:56px_56px] opacity-25" />

      <header className="sticky top-0 z-30 border-b border-sky-300/20 bg-slate-950/80 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-[1600px] flex-wrap items-center justify-between gap-3 px-4 py-3 md:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-300 to-blue-500 text-lg font-black text-slate-950">
              W.
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-sky-200/75">SecureBot</p>
              <h1 className="text-lg font-bold tracking-wide text-slate-100">SecureBot</h1>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search username, host, IP, alert ID, hash, process, case ID"
              className="w-full rounded-xl border border-sky-300/20 bg-slate-900/70 px-3 py-2 text-sm outline-none ring-cyan-300 transition focus:ring-1 md:w-[420px]"
            />
            <select
              value={selectedRole}
              onChange={(event) => setSelectedRole(event.target.value)}
              className="rounded-xl border border-sky-300/20 bg-slate-900/70 px-3 py-2 text-sm outline-none"
            >
              {roleAccess.map((role) => (
                <option key={role.role} value={role.role}>
                  {role.role}
                </option>
              ))}
            </select>
            <NavLink
              to="/reporting"
              className="rounded-xl border border-amber-300/40 bg-amber-400/15 px-3 py-2 text-sm font-semibold text-amber-100 transition hover:bg-amber-400/25"
            >
              Generate report
            </NavLink>
          </div>
        </div>

        <div className="mx-auto flex w-full max-w-[1600px] flex-wrap gap-2 px-4 pb-3 md:px-6">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `rounded-lg px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.13em] transition ${
                  isActive
                    ? 'bg-cyan-400/25 text-cyan-100'
                    : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700/80'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      </header>

      {toast ? (
        <div className="fixed right-4 top-24 z-40 animate-rise rounded-lg border border-cyan-300/30 bg-cyan-400/20 px-3 py-2 text-sm shadow-glow">
          <div className="flex items-center gap-3">
            <span>{toast}</span>
            <button
              onClick={dismissToast}
              className="rounded-md border border-cyan-200/40 px-2 py-0.5 text-xs"
            >
              Dismiss
            </button>
          </div>
        </div>
      ) : null}

      <main className="relative z-10 mx-auto flex w-full max-w-[1600px] flex-col gap-6 px-4 py-6 md:px-6">
        <Outlet />
      </main>
    </div>
  )
}
