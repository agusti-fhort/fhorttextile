// ⚠️ PÀGINA DE PROVA TEMPORAL (ESBORRABLE) — verifica aïllats els components del sistema visual
// comercial unificat abans d'aplicar-los a les 4 pantalles. Text literal a posta (no és UI enviada;
// s'esborrarà quan les pantalles adoptin els components). Ruta: /comercial/_kit.
import { useState } from 'react'
import { DocumentHeader, ModelCard, LineTable, RowBtn, DocumentSummary, minutesToHhMm, tecnicShort } from '../components/commercial'
import Badge from '../components/ui/Badge'
import PdfButton from '../components/ui/PdfButton'
import { selS, primaryBtn } from '../components/ui/buttons'

const MONO = 'IBM Plex Mono, monospace'
const secondaryBtn = { ...selS, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }

export default function CommercialKitDemo() {
  // Estat mínim per demostrar cel·les editables i el toggle de visibilitat.
  const [rows, setRows] = useState([
    { id: 1, concept: 'Patronatge base', qty: '1', price: '120,00', total: '120,00', visible: true, internal: { minutes: 526, tecnic: 'Anna Puig', cost: '87,66 €' } },
    { id: 2, concept: 'Escalat 6 talles', qty: '1', price: '90,00', total: '90,00', visible: true, internal: { minutes: 305, tecnic: 'Marc Soler i Vidal', cost: '50,83 €' } },
    { id: 3, concept: 'Ajust de fitting', qty: '2', price: '45,00', total: '90,00', visible: false, internal: { minutes: 45, tecnic: 'Berta', cost: '7,50 €' } },
  ])
  const setCell = (id, key, value) => setRows(rs => rs.map(r => r.id === id ? { ...r, [key]: value } : r))
  const toggleVis = (id) => setRows(rs => rs.map(r => r.id === id ? { ...r, visible: !r.visible } : r))
  const remove = (id) => setRows(rs => rs.filter(r => r.id !== id))

  const columns = [
    { key: 'concept', label: 'Concepte' },
    { key: 'qty', label: 'Unitats', align: 'right', width: 90, editable: true, inputMode: 'decimal',
      value: r => r.qty, onEdit: (r, v) => setCell(r.id, 'qty', v) },
    { key: 'price', label: 'Preu unit.', align: 'right', width: 110, editable: true, inputMode: 'decimal',
      value: r => r.price, onEdit: (r, v) => setCell(r.id, 'price', v) },
    { key: 'total', label: 'Import', align: 'right', width: 100,
      render: r => <b style={{ fontFamily: MONO }}>{r.total} €</b> },
  ]

  const renderActions = (r) => (
    <>
      <RowBtn icon={r.visible ? 'ti-eye' : 'ti-eye-off'} title={r.visible ? 'Amagar del document' : 'Mostrar al document'}
        active={r.visible} onClick={() => toggleVis(r.id)} />
      <RowBtn icon="ti-trash" title="Eliminar la línia" danger onClick={() => remove(r.id)} />
    </>
  )

  const internalLabels = { time: 'Temps', tecnic: 'Tècnic', cost: 'Cost' }

  return (
    <div style={{ maxWidth: 980, padding: '8px 0 40px' }}>
      <p style={{ fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--err)', marginBottom: 16 }}>
        ⚠️ Pàgina de prova temporal del sistema visual comercial (esborrable).
      </p>

      <DocumentHeader
        reference="OF-2026-0042"
        statusBadge={<Badge variant="gold">Enviada</Badge>}
        customer="BROWNIE · Brownie Fashion SL"
        actions={<>
          <button style={secondaryBtn}><i className="ti ti-plus" style={{ fontSize: 14 }} />Afegir ítems</button>
          <button style={secondaryBtn}><i className="ti ti-message-plus" style={{ fontSize: 14 }} />Comentari</button>
          <PdfButton label="PDF" onClick={() => {}} />
          <button style={primaryBtn}><i className="ti ti-send" style={{ fontSize: 14 }} />Emetre</button>
        </>}
      />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, margin: '20px 0' }}>
        <ModelCard reference="BRW-SS26-0001" name="Olivia Dress" meta="SS26 · Primavera"
          subtotalLabel="Subtotal model" subtotal="300,00 €">
          <LineTable columns={columns} rows={rows} renderActions={renderActions}
            showInternal internalLabels={internalLabels} />
        </ModelCard>

        <ModelCard reference="BRW-SS26-0007" name="Cropped Jacket" meta="SS26 · Primavera"
          subtotalLabel="Subtotal model" subtotal="90,00 €">
          <LineTable
            columns={columns}
            rows={[{ id: 9, concept: 'Confecció mostra', qty: '1', price: '90,00', total: '90,00', internal: { minutes: 132, tecnic: 'Joan Ferré', cost: '22,00 €' } }]}
            renderActions={renderActions} showInternal internalLabels={internalLabels} />
        </ModelCard>
      </div>

      <DocumentSummary
        lines={[
          { label: 'Base imposable', value: '390,00 €' },
          { label: 'I.V.A. 21%', value: '81,90 €' },
          { label: 'Import total', value: '471,90 €', strong: true },
        ]}
        showInternal internalLabel="Cost intern (només intern)" internalValue="168,49 €"
      />

      {/* Sanity dels helpers de format */}
      <p style={{ fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginTop: 24 }}>
        format · 526 → {minutesToHhMm(526)} · 45 → {minutesToHhMm(45)} · "Anna Puig" → {tecnicShort('Anna Puig')} · "Marc Soler i Vidal" → {tecnicShort('Marc Soler i Vidal')}
      </p>
    </div>
  )
}
