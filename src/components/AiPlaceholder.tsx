// La asistencia de IA se conecta en el incremento 5. Mientras tanto, el detalle ya funciona completo sin ella (R12.1)
const SECTIONS = [
  { title: "Causa probable", text: "Una explicación breve de qué pudo pasar en la sede." },
  { title: "Borrador de mensaje a la sede", text: "Un texto en español con los hallazgos concretos, listo para copiar." },
];

export default function AiPlaceholder() {
  return (
    <section aria-labelledby="ai-title" className="mt-14">
      <h2 id="ai-title" className="border-b border-ink pb-2 font-display text-lg font-bold">
        Asistencia de IA <span className="ml-2 text-sm font-medium text-graphite">IA – no vinculante</span>
      </h2>
      <div className="mt-4 grid gap-x-10 gap-y-6 md:grid-cols-2">
        {SECTIONS.map((section) => (
          <div key={section.title}>
            <h3 className="font-semibold">{section.title}</h3>
            <p className="mt-1 text-sm text-graphite">{section.text}</p>
            <p className="mt-3 text-sm font-medium">No disponible</p>
            <p className="text-sm text-graphite">La asistencia de IA todavía no está activada en esta versión.</p>
          </div>
        ))}
      </div>
    </section>
  );
}
