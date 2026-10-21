'use client'

import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Check, Copy } from 'lucide-react'
import styles from './TokenDemo.module.scss'

const SOURCE = `{
  "color": {
    "brand": {
      "500": { "$value": "#D4FF3A", "$type": "color" }
    },
    "action": {
      "primary": { "$value": "{color.brand.500}", "$type": "color" }
    }
  },
  "space": {
    "400": { "$value": "16px", "$type": "dimension" }
  },
  "motion": {
    "standard": { "$value": [0.2, 0, 0, 1], "$type": "cubicBezier" }
  }
}`

const OUTPUTS = {
  CSS: `:root {
  --color-brand-500: #d4ff3a;
  --color-action-primary: var(--color-brand-500);
  --space-400: 16px;
  --motion-standard: cubic-bezier(0.2, 0, 0, 1);
}`,
  SCSS: `$color-brand-500: #d4ff3a;
$color-action-primary: $color-brand-500;
$space-400: 16px;
$motion-standard: cubic-bezier(0.2, 0, 0, 1);`,
  Swift: `import SwiftUI

public enum Tokens {
  public static let colorBrand500 = Color(red: 0.831, green: 1.000, blue: 0.227)
  public static let colorActionPrimary = colorBrand500
  public static let space400: CGFloat = 16
}`,
  Compose: `object Tokens {
  val ColorBrand500 = Color(0xFFD4FF3A)
  val ColorActionPrimary = ColorBrand500
  val Space400 = 16.dp
  val MotionStandard = CubicBezierEasing(0.2f, 0f, 0f, 1f)
}`,
} as const

type Out = keyof typeof OUTPUTS

export function TokenDemo() {
  const [tab, setTab] = useState<Out>('CSS')
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(OUTPUTS[tab])
      setCopied(true)
      setTimeout(() => setCopied(false), 1400)
    } catch {}
  }

  return (
    <div className={styles.demo} data-reveal>
      <div className={styles.pane}>
        <header>
          <span className={styles.file}>tokens.json</span>
          <span className={styles.badge}>W3C DTCG</span>
        </header>
        <pre>
          <code>{SOURCE}</code>
        </pre>
      </div>

      <div className={styles.arrow} aria-hidden>
        <span>Style Dictionary</span>
        <motion.i animate={{ x: [0, 8, 0] }} transition={{ repeat: Infinity, duration: 1.6, ease: 'easeInOut' }}>
          →
        </motion.i>
      </div>

      <div className={styles.pane}>
        <header>
          <div className={styles.tabs} role="tablist">
            {(Object.keys(OUTPUTS) as Out[]).map((k) => (
              <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}>
                {tab === k && <motion.span layoutId="token-tab" className={styles.pill} />}
                <span>{k}</span>
              </button>
            ))}
          </div>
          <button className={styles.copy} onClick={copy} aria-label="Copy output">
            {copied ? <Check size={14} /> : <Copy size={14} />}
          </button>
        </header>
        <AnimatePresence mode="wait">
          <motion.pre
            key={tab}
            initial={{ opacity: 0, y: 8, filter: 'blur(4px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            exit={{ opacity: 0, y: -8, filter: 'blur(4px)' }}
            transition={{ duration: 0.25 }}
          >
            <code>{OUTPUTS[tab]}</code>
          </motion.pre>
        </AnimatePresence>
      </div>
    </div>
  )
}
