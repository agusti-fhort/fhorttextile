import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import paper from 'paper'

export default function PaperKonvaPoc() {
  const { t } = useTranslation()
  const canvasRef = useRef(null)
  const scopeRef = useRef(null)
  const [status, setStatus] = useState(t('poc_paper.status_loading'))

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return undefined

    const scope = new paper.PaperScope()
    scope.setup(canvas)
    scopeRef.current = scope

    const path = new scope.Path({
      segments: [[86, 146], [172, 72], [294, 116], [384, 68], [468, 154]],
      strokeColor: '#9c7a2f',
      strokeWidth: 4,
      fillColor: null,
    })
    path.smooth({ type: 'continuous' })
    new scope.Path.Circle({
      center: [468, 154],
      radius: 7,
      fillColor: '#9c7a2f',
    })
    scope.view.update()
    setStatus(t('poc_paper.status_ready'))

    return () => {
      scope.remove()
      scopeRef.current = null
    }
  }, [t])

  return (
    <main style={{ padding: 24, display: 'grid', gap: 16 }}>
      <header style={{ display: 'grid', gap: 6 }}>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: 'var(--fs-small)' }}>
          {t('poc_paper.kicker')}
        </p>
        <h1 style={{ margin: 0, color: 'var(--text-main)', fontSize: 'var(--fs-title)' }}>
          {t('poc_paper.title')}
        </h1>
        <p style={{ margin: 0, maxWidth: 760, color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
          {t('poc_paper.description')}
        </p>
      </header>

      <section
        style={{
          display: 'grid',
          gap: 10,
          width: 'min(100%, 860px)',
          padding: 12,
          border: '1px solid var(--border)',
          borderRadius: 8,
          background: 'var(--surface)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <strong style={{ color: 'var(--text-main)', fontSize: 'var(--fs-body)' }}>
            {t('poc_paper.paper_canvas')}
          </strong>
          <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-small)' }}>{status}</span>
        </div>
        <canvas
          ref={canvasRef}
          width={560}
          height={240}
          style={{
            width: '100%',
            maxWidth: 760,
            height: 320,
            background: 'var(--cream)',
            border: '1px solid var(--border)',
            borderRadius: 6,
          }}
        />
      </section>
    </main>
  )
}
