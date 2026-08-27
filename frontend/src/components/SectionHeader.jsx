// ============================================================
//  GRYPHONE — шапка раздела настроек
//  ------------------------------------------------------------
//  Переиспользуемый компонент заголовка раздела.
//  Шапка вынесена из прокручиваемой области и всегда видна.
// ============================================================

export default function SectionHeader({ title, description, icon }) {
  return (
    <div className="section-header">
      <div className="section-header-left">
        {icon && <span className="section-icon">{icon}</span>}
        <div>
          <h2 className="section-title">{title}</h2>
          {description && (
            <p className="section-desc">{description}</p>
          )}
        </div>
      </div>
    </div>
  )
}
