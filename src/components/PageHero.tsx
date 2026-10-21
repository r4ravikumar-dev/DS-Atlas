import { SplitHeading } from './SplitHeading'
import styles from './PageHero.module.scss'

interface Props {
  index: string
  eyebrow: string
  title: React.ReactNode
  intro: string
  stats?: { value: string; label: string }[]
  children?: React.ReactNode
}

export function PageHero({ index, eyebrow, title, intro, stats, children }: Props) {
  return (
    <section className={styles.hero}>
      <div className="container">
        <p className={styles.eyebrow} data-reveal>
          <span>{index}</span>
          {eyebrow}
        </p>
        <SplitHeading className={styles.title}>{title}</SplitHeading>
        <div className={styles.row}>
          <p className={styles.intro} data-reveal>
            {intro}
          </p>
          {stats && (
            <dl className={styles.stats} data-reveal>
              {stats.map((s) => (
                <div key={s.label}>
                  <dt>{s.label}</dt>
                  <dd>{s.value}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
        {children}
      </div>
    </section>
  )
}
