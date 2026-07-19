interface ParagraphRevealProps {
  paragraphs: string[]
  revealedCount: number
}

export function ParagraphReveal({ paragraphs, revealedCount }: ParagraphRevealProps) {
  return (
    <div className="space-y-4 mb-8">
      {paragraphs.slice(0, revealedCount).map((para, idx) => (
        <div
          key={idx}
          className="card p-6 slide-in"
        >
          <p className="text-gray-800 dark:text-gray-200 leading-relaxed text-lg select-none">
            {para}
          </p>
        </div>
      ))}
    </div>
  )
}
