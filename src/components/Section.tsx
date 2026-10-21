import styles from './Section.module.scss'

interface Props {
  id?: string
  kicker: string
  title: React.ReactNode
  intro?: string
  children: React.ReactNode
}

export function Section({ id, kicker, title, intro, children }: Props) {
  return (
    <section id={id} className={`container ${styles.section}`}>
      <header className={styles.head} data-reveal>
        <p className="mono">{kicker}</p>
        <h2>{title}</h2>
        {intro && <p className={styles.intro}>{intro}</p>}
      </header>
      {children}
    </section>
  )
}
