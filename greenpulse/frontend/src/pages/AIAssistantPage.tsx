import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { postAIQuery, fetchSystemHealth } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import { MessageSquare, Send, Cpu } from 'lucide-react'
import styles from './AIAssistantPage.module.css'

const SUGGESTED = [
  'Why is renewable generation lower today?',
  'Which asset currently has the worst performance?',
  'What is the expected generation in the next 6 hours?',
  'Are we producing a renewable energy surplus?',
  'Which turbines require maintenance?',
  'What caused the latest alert?',
]

// Section labels in the order they appear in the response
const SECTIONS = [
  'SUMMARY',
  'EVIDENCE',
  'ANALYSIS',
  'IMPACT',
  'RECOMMENDATION',
  'DATA SOURCES',
] as const

type Section = typeof SECTIONS[number]

const SECTION_ACCENT: Record<Section, string> = {
  SUMMARY: '#0B3D2E',
  EVIDENCE: '#147D64',
  ANALYSIS: '#4DA3D9',
  IMPACT: '#F59E0B',
  RECOMMENDATION: '#DC3545',
  'DATA SOURCES': '#5A6E68',
}

/**
 * Parse a structured AI answer into labelled sections.
 */
function parseSections(
  text: string
): { label: string; content: string; accent: string }[] {
  const result: {
    label: string
    content: string
    accent: string
  }[] = []

  const sectionPattern = SECTIONS.join('|')

  const pattern = new RegExp(
    `(${sectionPattern}):([\\s\\S]*?)(?=(?:${sectionPattern}):|$)`,
    'gi'
  )

  let match: RegExpExecArray | null = null
  let found = false

  while ((match = pattern.exec(text)) !== null) {
    const label = match[1].trim().toUpperCase() as Section

    let content = match[2].trim()

    /*
     * Clean duplicated recommendation labels.
     *
     * Examples removed:
     * AI
     * RECOMMENDATION:
     * AI RECOMMENDATION:
     */
    if (label === 'RECOMMENDATION') {
      content = content
        .split('\n')
        .map(line => line.trim())
        .filter(line => {
          if (!line) return false

          if (/^AI$/i.test(line)) return false

          if (/^RECOMMENDATION:?$/i.test(line)) return false

          if (/^AI\s+RECOMMENDATION:?$/i.test(line)) return false

          return true
        })
        .join('\n')
        .trim()
    }

    // Only render sections that actually contain content
    if (content) {
      result.push({
        label,
        content,
        accent: SECTION_ACCENT[label] ?? '#5A6E68',
      })

      found = true
    }
  }

  // If the AI response doesn't contain structured sections
  if (!found) {
    return [
      {
        label: '',
        content: text.trim(),
        accent: '#5A6E68',
      },
    ]
  }

  return result
}

/**
 * Render section content.
 */
function SectionContent({ text }: { text: string }) {
  const lines = text.split('\n')

  return (
    <div className={styles.sectionContent}>
      {lines.map((line, i) => {
        const stripped = line.trim()

        if (!stripped) return null

        if (
          stripped.startsWith('•') ||
          stripped.startsWith('-')
        ) {
          return (
            <div
              key={i}
              className={styles.bulletLine}
            >
              <span className={styles.bullet}>
                •
              </span>

              <span>
                {stripped.replace(/^[•\-]\s*/, '')}
              </span>
            </div>
          )
        }

        return (
          <p
            key={i}
            className={styles.sectionPara}
          >
            {stripped}
          </p>
        )
      })}
    </div>
  )
}

type HistoryEntry = {
  q: string
  a: string
  ts: string
  provider: string
  model: string
  duration_ms: number
}

export default function AIAssistantPage() {
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState<HistoryEntry[]>([])

  const { data: sysInfo } = useQuery({
    queryKey: ['sysInfo'],
    queryFn: fetchSystemHealth,
    staleTime: 30_000,
  })

  const mutation = useMutation({
    mutationFn: (q: string) => postAIQuery(q),

    onSuccess: (data, q) => {
      setHistory(h => [
        {
          q,
          a: data.answer,
          ts: data.timestamp,
          provider: data.ai_provider ?? 'simulation',
          model: data.model ?? '',
          duration_ms: data.duration_ms ?? 0,
        },
        ...h,
      ])

      setQuestion('')
    },
  })

  const ask = (q: string) => {
    if (!q.trim()) return

    mutation.mutate(q)
  }

  /*
   * Determine which provider should be shown in the header.
   *
   * Priority:
   *
   * 1. Actual provider returned by the latest AI response.
   * 2. Backend effective AI mode.
   * 3. Granite configured status.
   */

  const latestProvider = history[0]?.provider

  const graniteConfigured =
    sysInfo?.granite_configured === true ||
    sysInfo?.granite_configured === 'true' ||
    sysInfo?.granite_configured === 1 ||
    sysInfo?.granite_configured === '1'

  const isIBM =
    latestProvider === 'ibm' ||
    (!latestProvider &&
      (
        sysInfo?.effective_ai_mode === 'ibm' ||
        graniteConfigured
      ))

  const modeLabel = isIBM
    ? 'IBM GRANITE'
    : 'LOCAL REASONING'

  const modeBadge = isIBM
    ? 'success'
    : 'muted'

  return (
    <div className={styles.page}>

      {/* Header */}
      <div className={styles.header}>
        <h1>
          <MessageSquare size={18} />
          AI Assistant
        </h1>

        <div
          style={{
            display: 'flex',
            gap: 8,
            alignItems: 'center',
          }}
        >
          <StatusBadge
            label={modeLabel}
            variant={modeBadge as any}
          />

          {sysInfo && (
            <span className={styles.modelLabel}>
              <Cpu size={11} />

              {sysInfo.granite_model ??
                sysInfo.granite_configured}
            </span>
          )}
        </div>
      </div>

      {/* Suggested questions */}
      <div className={styles.suggested}>
        <div className={styles.suggestedLabel}>
          Suggested questions:
        </div>

        <div className={styles.chips}>
          {SUGGESTED.map(s => (
            <button
              key={s}
              className={styles.chip}
              onClick={() => ask(s)}
              disabled={mutation.isPending}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className={styles.inputRow}>
        <input
          className={styles.input}
          value={question}
          onChange={e =>
            setQuestion(e.target.value)
          }
          placeholder="Ask an operational question…"
          onKeyDown={e => {
            if (
              e.key === 'Enter' &&
              !e.shiftKey
            ) {
              e.preventDefault()
              ask(question)
            }
          }}
          disabled={mutation.isPending}
        />

        <button
          className={styles.sendBtn}
          onClick={() => ask(question)}
          disabled={
            mutation.isPending ||
            !question.trim()
          }
        >
          <Send size={15} />

          {mutation.isPending
            ? 'Analysing…'
            : 'Ask'}
        </button>
      </div>

      {/* Loading */}
      {mutation.isPending && (
        <div className={styles.thinking}>
          <span className={styles.thinkingDot} />
          <span className={styles.thinkingDot} />
          <span className={styles.thinkingDot} />

          <span className={styles.thinkingText}>
            GreenPulse AI is analysing operational data…
          </span>
        </div>
      )}

      {/* History */}
      <div className={styles.history}>
        {history.map((item, i) => {
          const sections = parseSections(item.a)

          const itemIsIBM =
            item.provider === 'ibm'

          return (
            <div
              key={i}
              className={styles.exchange}
            >

              {/* Question */}
              <div className={styles.question}>
                <span className={styles.qLabel}>
                  Q
                </span>

                {item.q}
              </div>

              {/* Structured answer */}
              <div className={styles.answerSections}>
                {sections.map((sec, j) => (
                  <div
                    key={j}
                    className={styles.section}
                  >
                    {sec.label && (
                      <div
                        className={styles.sectionLabel}
                        style={{
                          borderLeftColor:
                            sec.accent,
                          color: sec.accent,
                        }}
                      >
                        {sec.label}
                      </div>
                    )}

                    <SectionContent
                      text={sec.content}
                    />
                  </div>
                ))}
              </div>

              {/* Footer */}
              <div className={styles.answerMeta}>

                <span
                  className={
                    itemIsIBM
                      ? styles.providerIBM
                      : styles.providerSim
                  }
                >
                  {itemIsIBM
                    ? '⬡ IBM Granite'
                    : '◎ Local Reasoning'}
                </span>

                <span
                  className={styles.metaDivider}
                >
                  ·
                </span>

                <span>
                  {item.model.replace(
                    ' (local-reasoning)',
                    ''
                  )}
                </span>

                <span
                  className={styles.metaDivider}
                >
                  ·
                </span>

                <span>
                  {item.duration_ms > 0
                    ? `${item.duration_ms.toFixed(0)} ms`
                    : '< 1 ms'}
                </span>

                <span
                  className={styles.metaDivider}
                >
                  ·
                </span>

                <span>
                  {new Date(
                    item.ts
                  ).toLocaleTimeString()}
                </span>

              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}