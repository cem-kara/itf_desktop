import { useState, useCallback } from "react";

const DEFAULT = {
  BG_PRIMARY:"#0d1117", BG_SECONDARY:"#121820", BG_ELEVATED:"#1a2030",
  BORDER_PRIMARY:"#1e2d3d", BORDER_SECONDARY:"#253545", BORDER_FOCUS:"#3d8ef5",
  TEXT_PRIMARY:"#e8edf5", TEXT_SECONDARY:"#8fa3b8", TEXT_MUTED:"#4d6070", TEXT_DISABLED:"#263850",
  ACCENT:"#3d8ef5", ACCENT2:"#20c0d8",
  INPUT_BG:"#1a2030", INPUT_BORDER:"#1e2d3d",
  BTN_PRIMARY_BG:"#3d8ef5", BTN_PRIMARY_TEXT:"#060d1a",
  BTN_DANGER_TEXT:"#e85555", BTN_SUCCESS_TEXT:"#2ec98e",
  STATUS_SUCCESS:"#2ec98e", STATUS_WARNING:"#e8a030", STATUS_ERROR:"#e85555", STATUS_INFO:"#3d8ef5",
  RKE_PURP:"#a855f7",
};

const GROUPS = [
  { label:"Zemin",    keys:["BG_PRIMARY","BG_SECONDARY","BG_ELEVATED"] },
  { label:"Kenarlık", keys:["BORDER_PRIMARY","BORDER_SECONDARY","BORDER_FOCUS"] },
  { label:"Metin",    keys:["TEXT_PRIMARY","TEXT_SECONDARY","TEXT_MUTED","TEXT_DISABLED"] },
  { label:"Vurgu",    keys:["ACCENT","ACCENT2"] },
  { label:"Buton",    keys:["BTN_PRIMARY_BG","BTN_PRIMARY_TEXT","BTN_DANGER_TEXT","BTN_SUCCESS_TEXT"] },
  { label:"Input",    keys:["INPUT_BG","INPUT_BORDER"] },
  { label:"Durum",    keys:["STATUS_SUCCESS","STATUS_WARNING","STATUS_ERROR","STATUS_INFO","RKE_PURP"] },
];

function alpha(hex, a) {
  if (!hex || !hex.startsWith("#") || hex.length < 7) return hex;
  const r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${a})`;
}

export default function App() {
  const [T, setT] = useState(DEFAULT);
  const [activeTab, setActiveTab] = useState(0);
  const [filterSel, setFilterSel] = useState("Aktif");
  const [radio, setRadio] = useState(0);
  const [checks, setChecks] = useState([true, false, false]);
  const [progress, setProgress] = useState(68);
  const [panelOpen, setPanelOpen] = useState(true);
  const [copied, setCopied] = useState(false);
  const [hovBtn, setHovBtn] = useState(null);
  const [inputFocus, setInputFocus] = useState(null);

  const set = useCallback((k, v) => setT(p => ({ ...p, [k]: v })), []);

  const reset = () => setT(DEFAULT);
  const copyPython = () => {
    const lines = Object.entries(T).map(([k,v]) => `    ${k.padEnd(22)}= "${v}"`).join("\n");
    navigator.clipboard?.writeText(`class DarkTheme:\n${lines}`);
    setCopied(true); setTimeout(() => setCopied(false), 2000);
  };

  const btnStyle = (variant, id) => {
    const hov = hovBtn === id;
    const base = { border:"none", borderRadius:4, padding:"6px 16px", fontWeight:700, cursor:"pointer",
                   fontSize:12, fontFamily:"inherit", transition:"all 0.15s",
                   display:"inline-flex", alignItems:"center", gap:6 };
    if (variant==="action")    return {...base, background: hov?T.ACCENT2:T.BTN_PRIMARY_BG, color:T.BTN_PRIMARY_TEXT};
    if (variant==="secondary") return {...base, background: hov?T.BG_ELEVATED:"transparent", color:T.TEXT_SECONDARY, border:`1px solid ${T.BORDER_SECONDARY}`};
    if (variant==="success")   return {...base, background: hov?alpha(T.STATUS_SUCCESS,.25):alpha(T.STATUS_SUCCESS,.15), color:T.BTN_SUCCESS_TEXT, border:`1px solid ${alpha(T.STATUS_SUCCESS,.4)}`};
    if (variant==="danger")    return {...base, background: hov?alpha(T.STATUS_ERROR,.25):alpha(T.STATUS_ERROR,.15), color:T.BTN_DANGER_TEXT, border:`1px solid ${alpha(T.STATUS_ERROR,.4)}`};
    if (variant==="refresh")   return {...base, background: hov?T.BG_ELEVATED:"transparent", color:T.TEXT_SECONDARY, border:`1px solid ${T.BORDER_SECONDARY}`, padding:"6px 12px"};
    return base;
  };

  const Btn = ({ variant, id, children, onClick }) => (
    <button style={btnStyle(variant, id)} onClick={onClick}
      onMouseEnter={() => setHovBtn(id)} onMouseLeave={() => setHovBtn(null)}>
      {children}
    </button>
  );

  const inpStyle = (id) => ({
    background:T.INPUT_BG, border:`1px solid ${inputFocus===id ? T.BORDER_FOCUS : T.INPUT_BORDER}`,
    borderRadius:4, padding:"6px 10px", color:T.TEXT_PRIMARY, fontSize:12,
    outline:"none", fontFamily:"inherit", width:"100%", boxSizing:"border-box",
    transition:"border-color 0.15s",
  });

  const Section = ({ title, sub, children }) => (
    <div style={{ background:T.BG_SECONDARY, border:`1px solid ${T.BORDER_PRIMARY}`,
                  borderRadius:8, padding:"16px 18px", marginBottom:16 }}>
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:14 }}>
        <div style={{ width:3, height:20, background:T.ACCENT, borderRadius:2, flexShrink:0 }}/>
        <span style={{ color:T.ACCENT, fontSize:11, fontWeight:700, letterSpacing:"0.1em" }}>{title}</span>
        {sub && <span style={{ color:T.TEXT_MUTED, fontSize:10 }}>— {sub}</span>}
      </div>
      {children}
    </div>
  );

  const FormRow = ({ label, req, children }) => (
    <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:8 }}>
      <label style={{ color:T.TEXT_SECONDARY, fontSize:10, fontWeight:700, letterSpacing:"0.05em",
                      textTransform:"uppercase", minWidth:110, textAlign:"right", flexShrink:0 }}>
        {label}{req && <span style={{ color:T.STATUS_ERROR }}> *</span>}
      </label>
      <div style={{ flex:1 }}>{children}</div>
    </div>
  );

  const Code = ({ children }) => (
    <code style={{ background:T.BG_ELEVATED, color:T.TEXT_MUTED, fontSize:9,
                   padding:"1px 6px", borderRadius:3, fontFamily:"monospace", whiteSpace:"nowrap" }}>
      {children}
    </code>
  );

  const LabelRow = ({ code, sample, desc }) => (
    <div style={{ display:"grid", gridTemplateColumns:"130px 1fr 2fr", gap:"4px 14px",
                  alignItems:"center", marginBottom:6, paddingBottom:6,
                  borderBottom:`1px solid ${alpha(T.BORDER_PRIMARY,.7)}` }}>
      <Code>{code}</Code>
      <div>{sample}</div>
      <span style={{ color:T.TEXT_MUTED, fontSize:10, fontStyle:"italic" }}>{desc}</span>
    </div>
  );

  const TABLO = [
    ["PER-001","Dr. Ayşe Kaya",     "Radyoloji",  "Aktif",  "15.03.2019",T.STATUS_SUCCESS],
    ["PER-002","Uzm. Mehmet Demir", "Nükleer Tıp","İzinli", "08.09.2020",T.STATUS_WARNING],
    ["PER-003","Fiz. Zeynep Çelik", "Radyasyon",  "Aktif",  "22.11.2021",T.STATUS_SUCCESS],
    ["PER-004","Dr. Ali Yıldırım",  "Radyoloji",  "Pasif",  "01.04.2018",T.STATUS_ERROR],
  ];

  return (
    <div style={{ display:"flex", height:"100vh", overflow:"hidden",
                  background:T.BG_PRIMARY, fontFamily:"'JetBrains Mono',monospace", fontSize:12 }}>

      {/* ══ SOL — TEMA EDİTÖRÜ ══════════════════════════════════════ */}
      <div style={{ width:panelOpen?272:0, minWidth:panelOpen?272:0, transition:"all 0.2s",
                    overflow:"hidden", flexShrink:0, background:T.BG_SECONDARY,
                    borderRight:`1px solid ${T.BORDER_PRIMARY}`, display:"flex", flexDirection:"column" }}>

        <div style={{ padding:"14px 16px", borderBottom:`1px solid ${T.BORDER_PRIMARY}`, flexShrink:0 }}>
          <div style={{ color:T.TEXT_PRIMARY, fontSize:13, fontWeight:700, marginBottom:2 }}>🎨 Tema Editörü</div>
          <div style={{ color:T.TEXT_MUTED, fontSize:10 }}>Rengi tıkla → önizleme anında güncellenir</div>
        </div>

        <div style={{ flex:1, overflowY:"auto", padding:"12px 14px" }}>
          {GROUPS.map(g => (
            <div key={g.label} style={{ marginBottom:18 }}>
              <div style={{ color:T.ACCENT2, fontSize:9, fontWeight:700, letterSpacing:"0.15em",
                            textTransform:"uppercase", marginBottom:8, paddingBottom:4,
                            borderBottom:`1px solid ${T.BORDER_PRIMARY}` }}>
                {g.label}
              </div>
              {g.keys.map(k => (
                <div key={k} style={{ display:"flex", alignItems:"center", gap:8, marginBottom:7 }}>
                  <div style={{ position:"relative", flexShrink:0 }}>
                    <div style={{ width:30, height:30, borderRadius:5, background:T[k],
                                  border:`2px solid ${T.BORDER_SECONDARY}`, cursor:"pointer",
                                  overflow:"hidden", boxShadow:"0 1px 4px rgba(0,0,0,.5)" }}>
                      <input type="color" value={T[k]} onChange={e => set(k, e.target.value)}
                        style={{ width:"200%", height:"200%", border:"none", cursor:"pointer",
                                 transform:"translate(-25%,-25%)", opacity:0,
                                 position:"absolute", top:0, left:0 }}/>
                    </div>
                  </div>
                  <div style={{ flex:1, minWidth:0 }}>
                    <div style={{ color:T.TEXT_SECONDARY, fontSize:9, fontWeight:600,
                                  letterSpacing:"0.03em", marginBottom:2,
                                  whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>
                      {k}
                    </div>
                    <input value={T[k]}
                      onChange={e => { const v=e.target.value; if(/^#[0-9a-fA-F]{0,6}$/.test(v)) set(k,v); }}
                      style={{ ...inpStyle("hex_"+k), padding:"2px 6px", fontSize:10, height:22, fontFamily:"monospace" }}/>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>

        <div style={{ padding:"12px 14px", borderTop:`1px solid ${T.BORDER_PRIMARY}`,
                      display:"flex", gap:8, flexShrink:0 }}>
          <Btn variant="secondary" id="rst" onClick={reset}>↺ Sıfırla</Btn>
          <button onClick={copyPython} style={{
            flex:1, ...btnStyle("action","cpy"),
            background: copied ? T.STATUS_SUCCESS : T.BTN_PRIMARY_BG,
          }}>
            {copied ? "✓ Kopyalandı!" : "⎘ Python Kodu"}
          </button>
        </div>
      </div>

      {/* Sidebar toggle */}
      <button onClick={() => setPanelOpen(!panelOpen)} style={{
        position:"absolute", left:panelOpen?262:0, top:"50%", transform:"translateY(-50%)", zIndex:100,
        background:T.BG_ELEVATED, border:`1px solid ${T.BORDER_SECONDARY}`,
        borderRadius:"0 6px 6px 0", color:T.TEXT_MUTED, cursor:"pointer",
        padding:"10px 4px", fontSize:10, transition:"left 0.2s", lineHeight:1,
      }}>
        {panelOpen?"◀":"▶"}
      </button>

      {/* ══ SAĞ — CANLI ÖNİZLEME ══════════════════════════════════ */}
      <div style={{ flex:1, overflowY:"auto", overflowX:"hidden", background:T.BG_PRIMARY }}>

        {/* Başlık şeridi */}
        <div style={{ background:T.BG_SECONDARY, borderBottom:`1px solid ${T.BORDER_PRIMARY}`,
                      padding:"0 24px", height:52, display:"flex", alignItems:"center",
                      justifyContent:"space-between", position:"sticky", top:0, zIndex:10 }}>
          <span style={{ color:T.TEXT_PRIMARY, fontSize:15, fontWeight:700 }}>REPYS — Kontrol Önizleme</span>
          <span style={{ color:T.TEXT_MUTED, fontSize:10 }}>Soldan token rengi değiştir → her şey anında güncellenir</span>
        </div>

        <div style={{ padding:"20px 24px 40px", maxWidth:860 }}>

          {/* ── 1. BUTONLAR ─────────────────────────────────────── */}
          <Section title="BUTONLAR" sub="btn_action · btn_secondary · btn_success · btn_danger · btn_refresh · btn_filter · btn_filter_all">
            <div style={{ display:"flex", flexWrap:"wrap", gap:8, marginBottom:14 }}>
              <Btn variant="action"    id="b1">💾 Kaydet</Btn>
              <Btn variant="secondary" id="b2">✕ İptal</Btn>
              <Btn variant="success"   id="b3">✓ Onayla</Btn>
              <Btn variant="danger"    id="b4">🗑 Sil</Btn>
              <Btn variant="refresh"   id="b5">↺ Yenile</Btn>
              <button style={{ ...btnStyle("action","b6"), opacity:.4, cursor:"not-allowed" }} disabled>Devre Dışı</button>
            </div>
            <div style={{ display:"flex", gap:6, flexWrap:"wrap", alignItems:"center" }}>
              <span style={{ color:T.TEXT_MUTED, fontSize:10, marginRight:2 }}>btn_filter →</span>
              {["Tümü","Aktif","Pasif","İzinli"].map(m => (
                <button key={m} onClick={() => setFilterSel(m)} style={{
                  padding:"4px 14px", fontSize:11, borderRadius:4, cursor:"pointer", fontFamily:"inherit",
                  fontWeight:filterSel===m?700:500,
                  background:filterSel===m?alpha(T.ACCENT,.18):"transparent",
                  color:filterSel===m?T.ACCENT2:T.TEXT_SECONDARY,
                  border:`1px solid ${filterSel===m?T.ACCENT:T.BORDER_SECONDARY}`,
                  transition:"all 0.15s",
                }}>{m}</button>
              ))}
              <div style={{ width:1, height:20, background:T.BORDER_SECONDARY, margin:"0 8px" }}/>
              <span style={{ color:T.TEXT_MUTED, fontSize:10, marginRight:2 }}>btn_filter_all →</span>
              {["Bu Ay","Bu Yıl","Tüm Kayıtlar"].map(m => (
                <button key={m} style={{ padding:"4px 14px", fontSize:11, borderRadius:20, cursor:"pointer",
                  background:"transparent", color:T.TEXT_SECONDARY, fontFamily:"inherit",
                  border:`1px solid ${T.BORDER_SECONDARY}` }}>{m}</button>
              ))}
            </div>
          </Section>

          {/* ── 2. METİN GİRİŞ ALANLARI ─────────────────────── */}
          <Section title="METİN GİRİŞ ALANLARI" sub="input_field · input_search · input_text · read-only">
            <FormRow label="Ad Soyad" req>
              <input placeholder="Adı ve soyadını girin..."
                style={inpStyle("i1")} onFocus={() => setInputFocus("i1")} onBlur={() => setInputFocus(null)}/>
            </FormRow>
            <FormRow label="Kayıt No">
              <input value="URO-PER-001" readOnly
                style={{ ...inpStyle("ro"), background:T.BG_SECONDARY, color:T.TEXT_SECONDARY }}/>
            </FormRow>
            <FormRow label="Arama (search)">
              <input placeholder="🔍 Hızlı ara..."
                style={inpStyle("i3")} onFocus={() => setInputFocus("i3")} onBlur={() => setInputFocus(null)}/>
            </FormRow>
            <FormRow label="Açıklama (text)">
              <textarea rows={2} placeholder="Detaylı açıklama..."
                style={{ ...inpStyle("i4"), resize:"vertical", fontFamily:"inherit" }}
                onFocus={() => setInputFocus("i4")} onBlur={() => setInputFocus(null)}/>
            </FormRow>
          </Section>

          {/* ── 3. SEÇİM KONTROLLERİ ────────────────────────── */}
          <Section title="SEÇİM KONTROLLERİ" sub="input_combo · input_date · spin · double_spin">
            <div style={{ display:"flex", gap:14, flexWrap:"wrap" }}>
              {[
                ["Departman", <select style={{ ...inpStyle("c1"), height:34 }} onFocus={() => setInputFocus("c1")} onBlur={() => setInputFocus(null)}>
                  {["Radyoloji","Nükleer Tıp","Radyasyon Onkoloji"].map(o => <option key={o}>{o}</option>)}
                </select>],
                ["Giriş Tarihi", <input type="date" defaultValue="2024-01-15"
                  style={{ ...inpStyle("d1"), height:34 }} onFocus={() => setInputFocus("d1")} onBlur={() => setInputFocus(null)}/>],
                ["İzin (gün)", <input type="number" defaultValue={14} min={0} max={365}
                  style={{ ...inpStyle("s1"), height:34, width:90 }} onFocus={() => setInputFocus("s1")} onBlur={() => setInputFocus(null)}/>],
                ["Doz (mSv)", <input type="number" defaultValue="20.00" step="0.01"
                  style={{ ...inpStyle("s2"), height:34, width:90 }} onFocus={() => setInputFocus("s2")} onBlur={() => setInputFocus(null)}/>],
              ].map(([lbl, ctrl]) => (
                <div key={lbl} style={{ flex:"1 1 140px" }}>
                  <div style={{ color:T.TEXT_SECONDARY, fontSize:10, fontWeight:700,
                                letterSpacing:"0.05em", textTransform:"uppercase", marginBottom:5 }}>
                    {lbl}
                  </div>
                  {ctrl}
                </div>
              ))}
            </div>
          </Section>

          {/* ── 4. CHECKBOX & RADIO ─────────────────────────── */}
          <Section title="ONAY VE RADYO BUTONLARI" sub="checkbox · radiobutton · QButtonGroup">
            <div style={{ display:"flex", gap:40, flexWrap:"wrap" }}>
              <div>
                <div style={{ color:T.TEXT_MUTED, fontSize:10, letterSpacing:"0.1em", marginBottom:8 }}>CHECKBOX</div>
                {["Aktif personel","İzinde","Devre dışı"].map((lbl, i) => {
                  const dis = i === 2;
                  return (
                    <label key={lbl} onClick={() => !dis && setChecks(p => { const n=[...p]; n[i]=!n[i]; return n; })}
                      style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8,
                               cursor:dis?"not-allowed":"pointer", opacity:dis?.4:1 }}>
                      <div style={{ width:16, height:16, borderRadius:3, flexShrink:0,
                                    border:`1px solid ${checks[i]?T.ACCENT:T.BORDER_SECONDARY}`,
                                    background:checks[i]?T.ACCENT:T.INPUT_BG,
                                    display:"flex", alignItems:"center", justifyContent:"center",
                                    transition:"all 0.15s" }}>
                        {checks[i] && <span style={{ color:T.BTN_PRIMARY_TEXT, fontSize:10, fontWeight:900, lineHeight:1 }}>✓</span>}
                      </div>
                      <span style={{ color:T.TEXT_SECONDARY, fontSize:12 }}>{lbl}</span>
                    </label>
                  );
                })}
              </div>
              <div>
                <div style={{ color:T.TEXT_MUTED, fontSize:10, letterSpacing:"0.1em", marginBottom:8 }}>RADIOBUTTON</div>
                {["Tam zamanlı","Yarı zamanlı","Sözleşmeli"].map((lbl, i) => (
                  <label key={lbl} onClick={() => setRadio(i)}
                    style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8, cursor:"pointer" }}>
                    <div style={{ width:16, height:16, borderRadius:"50%", flexShrink:0,
                                  border:`1px solid ${radio===i?T.ACCENT:T.BORDER_SECONDARY}`,
                                  background:radio===i?T.ACCENT:T.INPUT_BG,
                                  display:"flex", alignItems:"center", justifyContent:"center",
                                  transition:"all 0.15s" }}>
                      {radio===i && <div style={{ width:6, height:6, borderRadius:"50%", background:T.BTN_PRIMARY_TEXT }}/>}
                    </div>
                    <span style={{ color:T.TEXT_SECONDARY, fontSize:12 }}>{lbl}</span>
                  </label>
                ))}
              </div>
            </div>
          </Section>

          {/* ── 5. ETİKETLER ───────────────────────────────── */}
          <Section title="ETİKETLER — 14 ÇEŞİT" sub="label_title · label_form · section_label · info_label · stat_* · donem · max_label · value">
            <LabelRow code="label_title"    desc="Sayfa başlığı — 15px, kalın, TEXT_PRIMARY"
              sample={<span style={{ color:T.TEXT_PRIMARY, fontSize:15, fontWeight:700 }}>Personel Yönetimi</span>}/>
            <LabelRow code="label_form"     desc="Form etiketi — 10px, uppercase, TEXT_SECONDARY"
              sample={<span style={{ color:T.TEXT_SECONDARY, fontSize:10, fontWeight:700, letterSpacing:"0.05em", textTransform:"uppercase" }}>TC KİMLİK NUMARASI *</span>}/>
            <LabelRow code="section_label"  desc="Bölüm başlık — 13px, letter-spacing"
              sample={<span style={{ color:T.TEXT_PRIMARY, fontSize:13, fontWeight:700, letterSpacing:"0.03em" }}>KİŞİSEL BİLGİLER</span>}/>
            <LabelRow code="info_label"     desc="Yardım / bilgi metni — 12px, TEXT_SECONDARY"
              sample={<span style={{ color:T.TEXT_SECONDARY, fontSize:12 }}>Son güncelleme: 12.05.2024</span>}/>
            <LabelRow code="footer_label"   desc="Dipnot — 10px, TEXT_MUTED"
              sample={<span style={{ color:T.TEXT_MUTED, fontSize:10 }}>REPYS v3.0.0 © 2024</span>}/>
            <LabelRow code="donem_label"    desc="Dönem göstergesi — ACCENT"
              sample={<span style={{ color:T.ACCENT, fontSize:12, fontWeight:600 }}>2024 / 1. Dönem</span>}/>
            <LabelRow code="max_label"      desc="Sarı uyarı — STATUS_WARNING, italic"
              sample={<span style={{ color:T.STATUS_WARNING, fontSize:11, fontStyle:"italic" }}>⚠ Maksimum izin hakkı aşıldı</span>}/>
            <LabelRow code="value"          desc="Veri değeri — 13px, TEXT_PRIMARY"
              sample={<span style={{ color:T.TEXT_PRIMARY, fontSize:12 }}>URO-XRY-SKP-10</span>}/>
            <LabelRow code="stat_label"     desc="İstatistik başlık — 12px, TEXT_MUTED"
              sample={<span style={{ color:T.TEXT_MUTED, fontSize:12 }}>Toplam Personel</span>}/>
            <LabelRow code="stat_value"     desc="İstatistik değer — 16px, TEXT_PRIMARY"
              sample={<span style={{ color:T.TEXT_PRIMARY, fontSize:16, fontWeight:700 }}>142</span>}/>
            <LabelRow code="stat_green"     desc="Pozitif — STATUS_SUCCESS"
              sample={<span style={{ color:T.STATUS_SUCCESS, fontSize:16, fontWeight:700 }}>↑ 28</span>}/>
            <LabelRow code="stat_red"       desc="Negatif — STATUS_ERROR"
              sample={<span style={{ color:T.STATUS_ERROR, fontSize:16, fontWeight:700 }}>↓ 3</span>}/>
            <LabelRow code="stat_highlight" desc="Vurgu KPI — ACCENT"
              sample={<span style={{ color:T.ACCENT, fontSize:16, fontWeight:700 }}>98.5%</span>}/>
            <LabelRow code="header_name"    desc="Kişi/kayıt adı — 14px, kalın"
              sample={<span style={{ color:T.TEXT_PRIMARY, fontSize:14, fontWeight:700 }}>Dr. Mehmet Yılmaz</span>}/>
          </Section>

          {/* ── 6. DURUM BADGE'LERİ ─────────────────────────── */}
          <Section title="DURUM BADGE'LERİ" sub="header_durum_aktif/pasif/izinli · get_status_color() dinamik">
            <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
              {[
                ["● AKTİF",       T.STATUS_SUCCESS, .15, .3],
                ["● PASİF",       T.STATUS_ERROR,   .15, .3],
                ["● İZİNLİ",      T.STATUS_WARNING, .15, .3],
                ["Tamamlandı",    T.STATUS_SUCCESS, .12, .25],
                ["Arızalı",       T.STATUS_ERROR,   .12, .25],
                ["Bakımda",       T.STATUS_WARNING, .12, .25],
                ["Kalibrasyonda", T.RKE_PURP,       .12, .3],
                ["Dış Serviste",  T.RKE_PURP,       .12, .3],
                ["Planlandı",     T.STATUS_INFO,    .12, .25],
              ].map(([lbl, clr, bgA, borA]) => (
                <span key={lbl} style={{ background:alpha(clr,bgA), border:`1px solid ${alpha(clr,borA)}`,
                  color:clr, borderRadius:6, padding:"3px 10px", fontSize:11, fontWeight:700, letterSpacing:"0.04em" }}>
                  {lbl}
                </span>
              ))}
            </div>
          </Section>

          {/* ── 7. TABLO ────────────────────────────────────── */}
          <Section title="TABLO" sub="QTableWidget · zebra satır · durum rengi · 9px/700w başlık">
            <div style={{ border:`1px solid ${T.BORDER_PRIMARY}`, borderRadius:6, overflow:"hidden" }}>
              <table style={{ width:"100%", borderCollapse:"collapse", background:T.BG_SECONDARY }}>
                <thead>
                  <tr>
                    {["PERSONEL ID","AD SOYAD","DEPARTMAN","DURUM","GİRİŞ TARİHİ"].map(h => (
                      <th key={h} style={{ color:T.TEXT_MUTED, fontSize:9, fontWeight:700, letterSpacing:"0.15em",
                                           textTransform:"uppercase", padding:"8px 12px",
                                           background:T.BG_PRIMARY, borderBottom:`1px solid ${T.BORDER_PRIMARY}`,
                                           textAlign:"left" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {TABLO.map(([id,ad,dep,durum,tarih,renk],i) => (
                    <tr key={id} style={{ background:i%2===0?T.BG_SECONDARY:T.BG_PRIMARY }}>
                      {[id,ad,dep].map(v => (
                        <td key={v} style={{ padding:"8px 12px", color:T.TEXT_SECONDARY, fontSize:11,
                                             borderBottom:`1px solid ${T.BORDER_PRIMARY}` }}>{v}</td>
                      ))}
                      <td style={{ padding:"8px 12px", fontSize:11, fontWeight:600, color:renk,
                                   borderBottom:`1px solid ${T.BORDER_PRIMARY}` }}>{durum}</td>
                      <td style={{ padding:"8px 12px", color:T.TEXT_MUTED, fontSize:11,
                                   borderBottom:`1px solid ${T.BORDER_PRIMARY}` }}>{tarih}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>

          {/* ── 8. GROUPBOX ─────────────────────────────────── */}
          <Section title="GROUPBOX" sub="group_box — ilgili alanları başlıklı çerçeve içinde gruplar">
            <div style={{ display:"flex", gap:12 }}>
              {[["Kişisel Bilgiler",["Ad Soyad","TC Kimlik No","Doğum Tarihi"]],
                ["Çalışma Bilgileri",["Unvan","Departman","Sicil No"]]].map(([bas,alanlar]) => (
                <div key={bas} style={{ flex:1, border:`1px solid ${T.BORDER_PRIMARY}`, borderRadius:8,
                                        padding:"16px 14px", background:T.BG_SECONDARY, position:"relative" }}>
                  <div style={{ position:"absolute", top:-10, left:12, background:T.BG_SECONDARY,
                                padding:"0 8px", color:T.TEXT_PRIMARY, fontSize:11, fontWeight:600 }}>
                    {bas}
                  </div>
                  {alanlar.map(alan => (
                    <div key={alan} style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8 }}>
                      <label style={{ color:T.TEXT_SECONDARY, fontSize:10, fontWeight:700,
                                      textTransform:"uppercase", letterSpacing:"0.04em", minWidth:90, textAlign:"right" }}>
                        {alan}
                      </label>
                      <input style={{ ...inpStyle("g"+alan), height:28, fontSize:11 }}
                        onFocus={() => setInputFocus("g"+alan)} onBlur={() => setInputFocus(null)}/>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </Section>

          {/* ── 9. SEKMELER ─────────────────────────────────── */}
          <Section title="SEKMELER (TAB)" sub="QTabWidget · aktif sekme ACCENT2 + alt kenarlık">
            <div style={{ display:"flex", borderBottom:`1px solid ${T.BORDER_PRIMARY}` }}>
              {["Genel Bilgiler","Teknik Bilgiler","Belgeler"].map((s, i) => (
                <div key={s} onClick={() => setActiveTab(i)} style={{
                  padding:"8px 16px", fontSize:12, cursor:"pointer",
                  color:activeTab===i?T.ACCENT2:T.TEXT_SECONDARY,
                  borderBottom:activeTab===i?`2px solid ${T.ACCENT}`:"2px solid transparent",
                  fontWeight:activeTab===i?700:500, transition:"all 0.15s",
                }}>{s}</div>
              ))}
            </div>
            <div style={{ background:T.BG_SECONDARY, border:`1px solid ${T.BORDER_PRIMARY}`,
                          borderTop:"none", padding:"16px", borderRadius:"0 0 6px 6px", minHeight:50 }}>
              <span style={{ color:T.TEXT_SECONDARY, fontSize:12 }}>
                {["Kişisel ve iletişim bilgileri burada gösterilir.",
                  "Bakım, kalibrasyon ve teknik veriler.",
                  "Yüklü belgeler ve dosyalar."][activeTab]}
              </span>
            </div>
          </Section>

          {/* ── 10. PROGRESS BAR ────────────────────────────── */}
          <Section title="İLERLEME ÇUBUĞU (PROGRESS)" sub="3px · BORDER_FOCUS rengi · slider ile canlı test">
            <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
              {[[progress,`Yükleme %${progress}`],[40,"Senkronizasyon %40"],[100,"Tamamlandı"]].map(([v,lbl],i) => (
                <div key={i}>
                  <div style={{ color:T.TEXT_SECONDARY, fontSize:11, marginBottom:4 }}>{lbl}</div>
                  <div style={{ background:T.BORDER_SECONDARY, borderRadius:2, height:4, overflow:"hidden" }}>
                    <div style={{ width:`${v}%`, height:"100%", borderRadius:2, transition:"width 0.3s",
                                  background:v===100?T.STATUS_SUCCESS:T.BORDER_FOCUS }}/>
                  </div>
                </div>
              ))}
              <div>
                <div style={{ color:T.TEXT_MUTED, fontSize:10, marginBottom:4 }}>
                  Sürükle → canlı test ({progress}%)
                </div>
                <input type="range" min={0} max={100} value={progress}
                  onChange={e => setProgress(+e.target.value)}
                  style={{ width:"100%", accentColor:T.ACCENT, cursor:"pointer" }}/>
              </div>
            </div>
          </Section>

          {/* ── 11. FILTER PANEL + SEPARATOR ────────────────── */}
          <Section title="FILTER PANEL + SEPARATOR" sub="filter_panel · separator — ayıraç çizgisi">
            <div style={{ background:T.BG_SECONDARY, border:`1px solid ${T.BORDER_PRIMARY}`,
                          borderRadius:10, padding:"12px 16px", display:"flex", gap:10,
                          alignItems:"center", flexWrap:"wrap" }}>
              <input placeholder="🔍 Cihaz ara..." style={{ ...inpStyle("fp"), maxWidth:200 }}
                onFocus={() => setInputFocus("fp")} onBlur={() => setInputFocus(null)}/>
              <select style={{ ...inpStyle("fs"), height:34, width:130 }}
                onFocus={() => setInputFocus("fs")} onBlur={() => setInputFocus(null)}>
                <option>Tümü</option><option>Aktif</option>
              </select>
              <select style={{ ...inpStyle("fd"), height:34, width:150 }}
                onFocus={() => setInputFocus("fd")} onBlur={() => setInputFocus(null)}>
                <option>Radyoloji</option><option>Nükleer Tıp</option>
              </select>
              <Btn variant="action" id="fpb">Filtrele</Btn>
              <Btn variant="secondary" id="fpbc">Temizle</Btn>
            </div>
            <div style={{ height:1, background:T.BORDER_SECONDARY, margin:"14px 0" }}/>
            <span style={{ color:T.TEXT_MUTED, fontSize:10 }}>↑ separator — S["separator"] yatay ayıraç</span>
          </Section>

          {/* ── 12. FOTOĞRAF ALANI ──────────────────────────── */}
          <Section title="FOTOĞRAF ALANI" sub="photo_area · photo_btn (= file_btn)">
            <div style={{ display:"flex", gap:16, alignItems:"flex-start" }}>
              <div style={{ width:90, height:120, border:`2px dashed ${T.BORDER_SECONDARY}`,
                            borderRadius:8, background:T.BG_ELEVATED,
                            display:"flex", alignItems:"center", justifyContent:"center",
                            flexShrink:0, color:T.TEXT_MUTED, fontSize:10, textAlign:"center" }}>
                Fotoğraf<br/>120×160
              </div>
              <div>
                <div style={{ color:T.TEXT_SECONDARY, fontSize:11, marginBottom:10 }}>
                  Kare fotoğraf, maks. 2 MB
                </div>
                <div style={{ display:"flex", gap:8 }}>
                  <Btn variant="action" id="pa1">📷 Fotoğraf Seç</Btn>
                  <Btn variant="danger" id="pa2">🗑 Kaldır</Btn>
                </div>
              </div>
            </div>
          </Section>

          {/* ── 13. İSTATİSTİK KARTLARI ─────────────────────── */}
          <Section title="İSTATİSTİK KARTLARI" sub="stat_label + stat_value/green/red/highlight · BG_ELEVATED zemin">
            <div style={{ display:"flex", gap:12, flexWrap:"wrap" }}>
              {[
                ["Toplam Personel","142",T.TEXT_PRIMARY,  "👥"],
                ["Aktif",          "128",T.STATUS_SUCCESS,"✅"],
                ["İzinli",         "11", T.ACCENT,        "📅"],
                ["Pasif",          "3",  T.STATUS_ERROR,  "❌"],
              ].map(([lbl,val,clr,ico]) => (
                <div key={lbl} style={{ background:T.BG_ELEVATED, border:`1px solid ${T.BORDER_PRIMARY}`,
                                        borderRadius:8, padding:"14px 18px", flex:"1 1 100px" }}>
                  <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:4 }}>
                    <span style={{ fontSize:14 }}>{ico}</span>
                    <span style={{ color:T.TEXT_MUTED, fontSize:11 }}>{lbl}</span>
                  </div>
                  <span style={{ color:clr, fontSize:18, fontWeight:700 }}>{val}</span>
                </div>
              ))}
            </div>
          </Section>

        </div>
      </div>
    </div>
  );
}
