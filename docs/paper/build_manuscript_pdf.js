'use strict';
// GenericChess v0.1 research PDF generator. Pure ASCII PDF, CJK via Adobe-GB1 CID.
// Run: node build_manuscript_pdf.js GenericChess_Research_Manuscript.md GenericChess_Research_Manuscript.pdf
const fs = require('fs');
function pdfFromMarkdown(source){
  const width=595.276,height=841.89,left=55,right=540,bottom=68;
  const pages=[[]];let y=788;
  function vis(s){return s.replace(/[·•]/g," / ").replace(/[−–—]/g,"-").replace(/×/g,"x").replace(/≈/g,"~").replace(/ε/g,"epsilon").replace(/θ/g,"theta").replace(/μ/g,"mu").replace(/π/g,"pi").replace(/σ/g,"sigma").replace(/ξ/g,"xi").replace(/λ/g,"lambda").replace(/ρ/g,"rho").replace(/Δ/g,"Delta").replace(/∈/g," in ").replace(/≤/g,"<=").replace(/≥/g,">=").replace(/→/g," -> ").replace(/←/g," <- ").replace(/∼/g,"~").replace(/Σ/g,"sum").replace(/∂/g,"d");}
  function measure(s,pt){let u=0;for(let i=0;i<s.length;i++){const p=s.codePointAt(i);if(p>65535){i++;u+=pt;continue;}const c=s[i];if(p>127)u+=pt;else if(c===" ")u+=pt*.27;else if(/[ilI\.,'`:;!|]/.test(c))u+=pt*.30;else if(/[MW@%#]/.test(c))u+=pt*.84;else if(/[0-9]/.test(c))u+=pt*.57;else if(/[A-Z]/.test(c))u+=pt*.69;else u+=pt*.54;}return u;}
  function wrap(s,pt,max){const chunks=s.match(/[A-Za-z0-9_./+:%#?&=~@-]+|./gs)||[];const out=[];let b="",w=0;function emit(){if(b.trim())out.push(b.trimEnd());b="";w=0;}
    for(const chunk of chunks){const cw=measure(chunk,pt);if(cw>max){for(const char of chunk){let z=measure(char,pt);if(w+z>max&&b)emit();b+=char;w+=z;}continue;}if(w+cw>max&&b)emit();b+=chunk;w+=cw;}emit();return out.length?out:[""];}
  function ensure(need){if(y-need<bottom){pages.push([]);y=789;}}
  function gap(pt){if(y-pt<bottom){pages.push([]);y=789;}else y-=pt;}
  function line(x,t,pt,leading,role="body",rgb="0.15 0.18 0.22"){ensure(leading);pages[pages.length-1].push({x,y,t:vis(t),pt,role,rgb});y-=leading;}
  function clean(s){return s.replace(/\*\*/g,"").replace(/\*([^*]+)\*/g,"$1").replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,(_m,a,b)=>a+" ("+b+")").replace(/^>\s*/,"").replace(/\t/g," ");}
  function heading(t,level){const pt=level===1?19.0:level===2?14.5:11.7,lead=level===1?27:level===2?22:17.5;gap(level===1?1:level===2?14:9);const rows=wrap(vis(t),pt,right-left);ensure(lead*Math.min(rows.length+1,3));for(const q of rows)line(left,q,pt,lead,"heading","0.09 0.17 0.26");gap(level===1?10:level===2?7:3);}
  function paragraph(t,style="body"){let pt=style==="table"?9.1:10.35,lead=style==="table"?14.0:16.2,text=vis(clean(t.trim()));if(!text)return;const bullet=/^([-*] |\d+[.] )/.test(text);let indent=style==="table"||bullet?13:0;let rows=wrap(text,pt,right-left-indent);ensure(Math.min(3,rows.length)*lead+3);for(let i=0;i<rows.length;i++)line(left+(i===0&&!bullet&&style==="body"?18:indent),rows[i],pt,lead,style,style==="table"?"0.19 0.25 0.30":"0.16 0.19 0.22");gap(style==="table"?2:6);}
  const lines=source.split(/\r?\n/);let collect=[];
  function flush(){if(collect.length){paragraph(collect.join(" "));collect=[];}}
  for(const raw of lines){const t=raw.trim();if(!t){flush();continue;}const h=t.match(/^(#{1,3})\s+(.*)/);if(h){flush();heading(clean(h[2]),h[1].length);continue;}
    if(t.startsWith("|")){flush();if(/^\|[\s\-:|]+\|$/.test(t))continue;const cells=t.split("|").slice(1,-1).map(x=>clean(x.trim()));paragraph(cells.join("  /  "),"table");continue;}
    if(/^([-*] |\d+[.] )/.test(t)){flush();paragraph(t);continue;}
    if(t.startsWith("**")&&t.endsWith("**")&&t.length<190){flush();paragraph(t);continue;}
    collect.push(t);
  }flush();
  const count=pages.length;
  function unihex(s){let out="";for(let i=0;i<s.length;i++)out+=s.charCodeAt(i).toString(16).padStart(4,"0").toUpperCase();return out;}
  function asciihex(s){let out="";for(let i=0;i<s.length;i++)out+=s.charCodeAt(i).toString(16).padStart(2,"0").toUpperCase();return out;}
  function paintText(x,z,t,pt,color,role){let parts=[],cur=x;for(const run of(t.match(/[\x00-\x7F]+|[^\x00-\x7F]+/g)||[])){let a=/^[\x00-\x7F]+$/.test(run),font=a?(role==="heading"?"/F3":"/F2"):"/F1";parts.push("BT "+color+" rg "+font+" "+pt.toFixed(2)+" Tf 1 0 0 1 "+cur.toFixed(2)+" "+z.toFixed(2)+" Tm <"+(a?asciihex(run):unihex(run))+"> Tj ET");cur+=measure(run,pt);}return parts.join("\n");}
  const obj=[];obj[1]="<< /Type /Catalog /Pages 2 0 R >>";obj[3]="<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light /Encoding /UniGB-UCS2-H /DescendantFonts [4 0 R] >>";obj[4]="<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light /CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 2 >> /DW 1000 >>";obj[5]="<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>";obj[6]="<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>";
  const refs=[];for(let p=0;p<count;p++){let pageid=7+2*p,contid=pageid+1;refs.push(pageid+" 0 R");const cmds=[];
    if(p){cmds.push("0.78 0.80 0.83 RG 0.5 w 55 810 m 540 810 l S");cmds.push(paintText(55,821,"GenericChess | Research Manuscript v0.1",8.0,"0.49 0.52 0.56","small"));}
    for(const v of pages[p])cmds.push(paintText(v.x,v.y,v.t,v.pt,v.rgb,v.role));
    cmds.push("0.82 0.83 0.85 RG 0.4 w 55 52 m 540 52 l S");
    cmds.push(paintText(55,38,"Working draft | 2026-10-23",8.1,"0.49 0.52 0.56","small"));
    cmds.push(paintText(498,38,(p+1)+" / "+count,8.1,"0.49 0.52 0.56","small"));
    const stream=cmds.join("\n")+"\n";
    obj[pageid]="<< /Type /Page /Parent 2 0 R /MediaBox [0 0 "+width+" "+height+"] /Resources << /Font << /F1 3 0 R /F2 5 0 R /F3 6 0 R >> >> /Contents "+contid+" 0 R >>";
    obj[contid]="<< /Length "+stream.length+" >>\nstream\n"+stream+"endstream";
  }
  obj[2]="<< /Type /Pages /Count "+count+" /Kids ["+refs.join(" ")+"] >>";
  let pdf="%PDF-1.4\n%ASCII\n";const offsets=[0];for(let i=1;i<obj.length;i++){offsets[i]=pdf.length;pdf+=i+" 0 obj\n"+obj[i]+"\nendobj\n";}
  const xref=pdf.length;pdf+="xref\n0 "+obj.length+"\n0000000000 65535 f \n";for(let i=1;i<obj.length;i++)pdf+=String(offsets[i]).padStart(10,"0")+" 00000 n \n";
  pdf+="trailer\n<< /Root 1 0 R /Size "+obj.length+" >>\nstartxref\n"+xref+"\n%%EOF\n";
  return {pdf,pages:count,objects:obj.length,ascii:[...pdf].every(c=>c.charCodeAt(0)<128)};
}
const source=fs.readFileSync(process.argv[2]||'GenericChess_Research_Manuscript.md','utf8');
const out=pdfFromMarkdown(source);
if(!out.ascii)throw new Error('PDF must be ASCII serializable');
fs.writeFileSync(process.argv[3]||'GenericChess_Research_Manuscript.pdf',out.pdf,'ascii');
console.log(out.pages+' pages; '+out.pdf.length+' bytes');
