import POMBrowser from '../components/POMBrowser/POMBrowser'

export default function POMs() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 100px)' }}>
      <div style={{ marginBottom: '0.8rem' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4 }}>POM Systems</h1>
        <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>
          Catàleg de Points of Measure per tipus de prenda
        </p>
      </div>
      <div style={{
        flex: 1, overflow: 'hidden',
        background: 'var(--white)',
        border: '0.5px solid #e4e4e2',
        borderRadius: 12,
      }}>
        <POMBrowser mode="explore" />
      </div>
    </div>
  )
}
