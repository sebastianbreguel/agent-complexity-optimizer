# React (web and React Native)

Rendering cost is (work per render) x (number of renders). Reduce either one, and measure with the React DevTools Profiler before and after. For a full React health check, `npx -y react-doctor@latest .` complements this skill.

## Work per render

- **Filtering, sorting, or reducing large collections in the component body:** runs on every render. Wrap in `useMemo` with the real inputs as dependencies, or derive on the server / in a selector. *render-derived-work*
- **Rendering thousands of rows:** virtualize (`@tanstack/react-virtual`, `react-window`; `FlatList` / `FlashList` in React Native) instead of mapping everything.
- **Expensive work in `useEffect` that sets state right away** (derived state): compute during render (memoized) instead of effect + state, which renders twice.
- **Creating heavy objects on every render** (formatters like `new Intl.NumberFormat`, regexes, big config objects): hoist to module scope or `useMemo`.

## Number of renders

- **Inline objects/arrays/functions passed to memoized children** (`style={{...}}`, `options={[...]}`, `onClick={() => ...}`): they break `React.memo`. Stabilize with `useMemo` / `useCallback` only where a memoized child or an effect dependency needs it.
- **Context values that change every render** (`value={{ user, setUser }}`): every consumer re-renders. Memoize the value, or split fast-changing and slow-changing contexts.
- **State kept too high:** typing in one input re-renders the whole page. Move state down to the component that uses it.
- **Missing or unstable `key` in lists** (`key={index}` on reorderable lists, `key={Math.random()}`): React remounts items. Use a stable id.
- **Data fetching waterfalls** (child fetches only after parent's fetch finishes): fetch in parallel at the route/loader level, or use a data library (TanStack Query, SWR, RSC) that dedupes and caches.
- **Subscribing to a whole store** (`useSelector(state => state)`): select only the slice the component needs.

## Detect

The scanner flags `render-derived-work` in PascalCase components. Also search for `useEffect(` blocks that only call a setter, `value={{` on providers, `key={index}` / `key={i}`, and lists rendered without virtualization. The React Compiler (when enabled) memoizes automatically; don't add manual memoization it already covers.

## Measure

React DevTools Profiler (commit durations, "why did this render"), Chrome DevTools Performance panel, and `<Profiler onRender>` for timings in code. Details in `../measuring.md`.
