// Local authoring with the bundled @oai/artifact-tool. No network calls.
// Set FAEHUB_ARTIFACT_MODULE to the module file when using another installation.
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const root = path.resolve(import.meta.dirname, '..');
const modulePath = process.env.FAEHUB_ARTIFACT_MODULE || 'C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const { Presentation, PresentationFile } = await import(pathToFileURL(modulePath).href);
const build = process.env.FAEHUB_SLIDE_BUILD || path.join(root, '.presentation-build');
await fs.mkdir(build, { recursive: true });
const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const blue='#1647D8', ink='#182230', pale='#DCE8FF';
function box(s,x,y,w,h,fill='none',stroke='none',geometry='rect') {
  return s.shapes.add({geometry,position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width:stroke==='none'?0:1.5,style:'solid'}});
}
function txt(s,text,x,y,w,h,size=26,bold=false,color=ink,align='left') {
  const o=box(s,x,y,w,h); o.text=text;
  o.text.style={typeface:'Arial',fontSize:size,bold,color,alignment:align}; return o;
}
function base(n,title) {
  const s=deck.slides.add();s.background.fill='#FFFFFF';
  txt(s,'FAEHUB+ / PROJETO FINAL',64,35,900,30,17,true,blue);
  txt(s,String(n).padStart(2,'0'),1160,35,55,30,18,false,blue);
  box(s,64,80,1152,2,pale);
  txt(s,title,64,108,1152,70,44,true);
  return s;
}
function line(s,x,y,w,h,color=blue) {return box(s,x,y,w,h,color);}
function note(s,text){s.speakerNotes.text=text;}
let s=deck.slides.add();s.background.fill=blue;
txt(s,'PROJETO FINAL DE DESENVOLVIMENTO DE SISTEMAS',64,54,1140,40,19,true,'#FFFFFF');
txt(s,'FaeHub+',64,188,750,125,96,true,'#FFFFFF');
txt(s,'Sistema web de gestão escolar',64,325,740,75,35,false,'#FFFFFF');
txt(s,'ETESC / FAETEC Santa Cruz',64,414,740,45,25,false,pale);
line(s,64,500,700,2,'#4D7CFE');
txt(s,'Thiago Souza Zotti\nJonathan Samuel Martins Tannes',64,532,820,110,28,false,'#FFFFFF');
const logo=await fs.readFile(path.join(root,'static/logo-faehub.webp'));
s.images.add({blob:logo.buffer.slice(logo.byteOffset,logo.byteOffset+logo.byteLength),contentType:'image/webp',alt:'Logo do FaeHub+',fit:'contain',position:{left:875,top:220,width:310,height:310}});
note(s,'Thiago: apresentar o grupo e o sistema. Somos Thiago Souza Zotti e Jonathan Samuel Martins Tannes. O FaeHub+ reúne acompanhamento e gestão escolar em espaços próprios para cada perfil. Fonte: README.md.');
s=base(2,'Objetivo');
txt(s,'Centralizar o acompanhamento acadêmico e as rotinas escolares em uma aplicação web com acesso por perfil.',64,205,1130,115,32);
const goals=[['Consulta acadêmica','Boletim, frequência e horários.'],['Rotina do professor','Notas, chamada e atividades.'],['Gestão escolar','Turmas, matrículas e períodos letivos.'],['Comunicação','Mensagens, comunicados e acompanhamento familiar.']];
goals.forEach(([a,b],i)=>{const x=64+(i%2)*592,y=358+Math.floor(i/2)*142;line(s,x,y,550,3);txt(s,a,x,y+17,550,38,26,true,blue);txt(s,b,x,y+62,550,78,25);});
note(s,'Thiago: explicar o objetivo geral e relacionar cada objetivo às telas existentes. Fonte: README.md e navegação NAV em app.py.');
s=base(3,'Justificativa');
txt(s,'PROBLEMA',64,205,540,35,22,true,blue);
txt(s,'Informações em diferentes registros e canais dificultam a consulta e o acompanhamento escolar.',64,259,530,210,32);
txt(s,'RELEVÂNCIA',674,205,540,35,22,true,blue);
txt(s,'Um ambiente central facilita o acesso ao histórico, organiza registros e aproxima a comunicação entre escola e família.',674,259,530,230,29);
line(s,64,520,1150,2,pale);
txt(s,'CONTEXTO DE APLICAÇÃO',64,548,1150,35,22,true,blue);
txt(s,'Projeto para o contexto da ETESC / FAETEC Santa Cruz, com espaços para aluno, responsável, professor e direção.',64,592,1150,90,26);
note(s,'Thiago: a dispersão de informações é a motivação do projeto, não uma conclusão de pesquisa de campo. Não afirmar adoção institucional nem ganhos medidos. Fonte do contexto: README.md.');
s=base(4,'Diagrama de casos de uso');
// UML permits actors as classifiers marked with the actor stereotype.
const boundary=box(s,290,193,926,441,'none',blue);txt(s,'FaeHub+',310,200,850,30,21,true,blue);
function actor(label,x,y){const a=box(s,x,y,178,66,pale,blue);txt(s,'«actor»\n'+label,x+6,y+4,166,59,20,true,ink,'center');return a;}
function use(label,x,y,w=345){const o=box(s,x,y,w,75,'#FFFFFF',blue,'ellipse');txt(s,label,x+18,y+14,w-36,54,21,false,ink,'center');return o;}
const a=actor('Aluno',64,250),r=actor('Responsável',64,353),p=actor('Professor',64,456),d=actor('Direção',64,559);
const u1=use('Consultar boletim\ne frequência',336,253),u2=use('Consultar horários\ne enviar atividades',821,253),u3=use('Registrar notas\ne chamada',336,392),u4=use('Publicar atividades',821,392),u5=use('Gerenciar estrutura\ne usuários',336,531),u6=use('Consultar relatórios',821,531);
function connect(s,a,b,from='right',to='left',kind='straight'){return s.shapes.connect(a,b,{kind,fromSide:from,toSide:to,line:{fill:ink,width:1.4,style:'solid'}});}
connect(s,a,u1);connect(s,r,u1);connect(s,p,u3);connect(s,d,u5);
// The second association in each row follows a dedicated gap between use cases.
function segment(s,x1,y1,x2,y2){box(s,Math.min(x1,x2),Math.min(y1,y2),Math.max(1.4,Math.abs(x2-x1)),Math.max(1.4,Math.abs(y2-y1)),ink);}
for(const [startY,routeY,endY] of [[270,238,253],[480,374,392],[582,513,531]]){
  segment(s,242,startY,269,startY);segment(s,269,startY,269,routeY);
  segment(s,269,routeY,993,routeY);segment(s,993,routeY,993,endY);
}
txt(s,'Recorte dos casos principais. A autenticação é precondição comum a todas as ações.',64,654,1152,35,19);
note(s,'Jonathan: explicar os atores e casos de uso. A conta autenticada define as permissões. O responsável consulta apenas o estudante vinculado. Mensagens e outros módulos foram omitidos para clareza. Fonte: app.py e README.md.');
s=base(5,'Diagrama de banco de dados');
// Academic core excerpt. Field names and links follow academic_core.py.
function entity(name,fields,x,y,w=230){const o=box(s,x,y,w,141,'#FFFFFF',blue);box(s,x,y,w,36,pale);txt(s,name,x+8,y+5,w-16,30,19,true,blue);txt(s,fields,x+8,y+44,w-16,93,17);return o;}
const st=entity('students','PK id\nregistration',64,213),en=entity('enrollments','PK id\nFK student_id\nFK class_id',354,213),cl=entity('classes','PK id\ncode',644,213),cs=entity('class_subjects','PK id\nFK class_id\nFK subject_id',934,213);
const sc=entity('assessment_scores','PK id\nFK assessment_id\nFK enrollment_id\nscore',354,455),as=entity('assessments','PK id\nFK class_subject_id\nFK academic_period_id',644,455),su=entity('subjects','PK id\nname',934,455),ap=entity('academic_periods','PK id\nname',64,455);
connect(s,st,en);connect(s,en,cl);connect(s,cl,cs);connect(s,en,sc,'bottom','top');connect(s,cs,su,'bottom','top');connect(s,as,sc,'left','right');connect(s,cs,as,'bottom','top','elbow');
segment(s,179,596,179,626);segment(s,179,626,759,626);segment(s,759,626,759,596);
function card(t,x,y,w=60){txt(s,t,x,y,w,25,17,true,blue);}
card('1',298,271);card('0..*',314,300);card('0..*',586,271);card('1',621,300);card('1',877,271);card('0..*',885,300);
card('1',472,365);card('0..*',472,419);card('0..*',1053,365);card('1',1053,419);card('1',602,486);card('0..*',586,548);card('1',193,600);card('0..*',770,600);card('1',921,365);card('0..*',764,419);
txt(s,'Recorte do núcleo acadêmico em PostgreSQL / Supabase. PK: chave primária. FK: chave estrangeira.',64,650,1152,28,18);
txt(s,'1 e 0..*: cardinalidades. Usuários, aulas, frequência e outras tabelas foram omitidos.',64,680,1152,28,18);
note(s,'Jonathan: matrícula associa estudante e turma; class_subjects associa turma e disciplina; assessments associa a oferta ao período; assessment_scores associa avaliação e matrícula. Cardinalidades representam vínculos possíveis. Fonte: academic_core.py, migrações 20260925151550 e 20260926133712.');
s=base(6,'Demonstração prática');
txt(s,'Thiago',64,208,530,44,32,true,blue);txt(s,'Aluno e família',64,260,530,38,23,false,blue);
txt(s,'1. Acessar o espaço do aluno.\n\n2. Consultar boletim, frequência e horário.\n\n3. Abrir atividades e comunicados.\n\n4. Mostrar a visão do responsável.',64,317,530,276,25);
txt(s,'Jonathan',675,208,530,44,32,true,blue);txt(s,'Professor e direção',675,260,530,38,23,false,blue);
txt(s,'1. Acessar o espaço do professor.\n\n2. Mostrar notas, chamada e atividades.\n\n3. Acessar o espaço da direção.\n\n4. Mostrar estrutura e relatórios.',675,317,530,276,25);
line(s,64,621,1152,2,pale);txt(s,'Preparação: ensaiar com contas de demonstração e levar slides e gravação de backup.',64,649,1152,42,21);
note(s,'Ambos participam. Divisão sugerida: Thiago apresenta slides 1 a 3, Jonathan apresenta slides 4 e 5. Ensaiar fluxos antes. O banco é remoto: conferir internet e configuração. Levar gravação e slides em pendrive. Não mostrar senhas, tokens ou dados pessoais. Fonte: README.md e docs/apresentacao-projeto-final.md.');
await (await PresentationFile.exportPptx(deck)).save(path.join(build,'candidate.pptx'));
for(let i=0;i<deck.slides.items.length;i++){
  const png=await deck.export({slide:deck.slides.items[i],format:'png',scale:1});
  await fs.writeFile(path.join(build,`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));
}
console.log(JSON.stringify({candidate:path.join(build,'candidate.pptx'),slides:deck.slides.items.length}));
