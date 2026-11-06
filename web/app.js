const studioBase=new URL('./',window.location.href);
const audioURL=path=>path?new URL(path.replace(/^\//,''),studioBase).href:'';
const $=id=>document.getElementById(id);
let project={name:'Untitled book',chapters:[{title:'Chapter One',text:'',status:'Draft'}]}, selected=0, timer, busy=false;
async function api(path,body){const r=await fetch(new URL('api/'+path,studioBase),body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw Error(data.error||'Request failed');return data}
function current(){return project.chapters[selected]}
function list(){ $('chapters').replaceChildren(); $('count').textContent=project.chapters.length+' chapters';project.chapters.forEach((c,i)=>{const b=document.createElement('button');b.className=i===selected?'active':'';b.textContent=String(i+1).padStart(2,'0')+'  '+c.title;const s=document.createElement('small');s.textContent=c.status;b.append(s);b.onclick=()=>{selected=i;render()};$('chapters').append(b)})}
function metrics(){$('words').textContent=(current().text.trim().match(/\S+/g)||[]).length+' words · '+current().text.length.toLocaleString()+' characters'}
function render(){$('book').value=project.name;$('title').value=current().title;$('text').value=current().text;$('position').textContent='CHAPTER '+String(selected+1).padStart(2,'0');$('status').textContent=current().status;$('audio').hidden=!current().audio;$('audio').src=audioURL(current().audio);$('download').hidden=!current().audio;$('download').href=audioURL(current().audio);list();metrics()}
let saveQueue=Promise.resolve();
function save(){clearTimeout(timer);$('save').textContent='Saving…';timer=setTimeout(()=>{const snapshot=JSON.parse(JSON.stringify(project));saveQueue=saveQueue.catch(()=>{}).then(()=>api('project',snapshot)).then(()=>{$('save').textContent='Saved locally'}).catch(e=>{$('save').textContent='Save failed';$('message').textContent=e.message})},400)}
for(const id of ['title','text'])$(id).oninput=()=>{current()[id]=$(id).value;current().status='Draft';delete current().audio;$('audio').hidden=true;$('download').hidden=true;$('status').textContent='Draft';list();metrics();save()};
$('book').oninput=()=>{project.name=$('book').value;save()};
$('add').onclick=()=>{project.chapters.push({title:'Chapter '+(project.chapters.length+1),text:'',status:'Draft'});selected=project.chapters.length-1;render();save()};
$('import').onclick=()=>$('file').click();
$('file').onchange=async()=>{const f=$('file').files[0];if(!f)return;try{if(f.size>4000000)throw Error('Please use a manuscript under 4 MB');const result=await api('import',{name:f.name,text:await f.text()});if(!result.chapters.length)throw Error('This manuscript has no text');if(project.chapters.some(c=>c.text.trim())&&!confirm('Replace the current manuscript? Export a project backup first if you need to keep it.'))return;project={name:f.name.replace(/\.[^.]+$/,''),chapters:result.chapters};selected=0;render();save()}catch(e){$('message').textContent=e.message}finally{$('file').value=''}};
$('sample').onclick=()=>{if(project.chapters.some(c=>c.text.trim())&&!confirm('Replace the current manuscript with the sample?'))return;project={name:'The Art of Beginning',chapters:[{title:'Chapter One — The Quiet Page',text:'Every story begins with a moment of stillness. Before the first word, before the first voice, there is a page waiting to become something more.\n\nThat morning, the light fell across the desk in long golden lines. She opened her notebook, took a breath, and began.',status:'Draft'},{title:'Chapter Two — Finding a Voice',text:'The words had always been there. Now, spoken aloud, they carried a different kind of weight. A pause became a doorway. A sentence became a journey.',status:'Draft'}]};selected=0;render();save()};
async function generate(preview){if(busy)return;const chapter=current(), source=chapter.text, text=preview?source.slice(0,1000):source;if(!text.trim()){$('message').textContent='Add some chapter text first.';return}busy=true;$('generate').disabled=$('preview').disabled=true;$('message').textContent='Creating audio on this computer…';try{const result=await api('generate',{text,voice:$('voice').value});if(chapter.text!==source){$('message').textContent='Text changed during generation. Generate again for the updated text.';return}chapter.audio=result.url;chapter.status=preview?'Preview ready':'Audio ready';render();save();$('message').textContent=preview?'Opening preview ready.':'Chapter audio ready to review.'}catch(e){$('message').textContent=e.message}finally{busy=false;$('generate').disabled=$('preview').disabled=false}}
$('generate').onclick=()=>generate(false);$('preview').onclick=()=>generate(true);
$('approve').onclick=()=>{if(!current().audio){$('message').textContent='Generate and listen to chapter audio first.';return}if(current().status==='Preview ready'){$('message').textContent='Generate the full chapter before marking it reviewed.';return}current().status='Reviewed';render();save()};
$('export').onclick=()=>{const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify(project,null,2)],{type:'application/json'}));a.href=url;a.download=(project.name||'author-narrator')+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
async function init(){render();try{const saved=await api('project');if(saved?.chapters?.length){project=saved;render()}}catch(e){$('message').textContent='Could not load the saved project: '+e.message}try{const result=await api('voices');for(const name of result.voices){const o=document.createElement('option');o.value=o.textContent=name;$('voice').append(o)}}catch(e){$('message').textContent=e.message}}
init();

const brandTitle = document.querySelector('.brand-title');
const brandTagline = document.querySelector('.brand small');
const fitBrandTitle = () => {
    const titleWidth = brandTitle.offsetWidth;
    if (titleWidth) {
        brandTitle.style.transform = `scaleX(${brandTagline.offsetWidth / titleWidth})`;
    }
};
new ResizeObserver(fitBrandTitle).observe(brandTagline);
document.fonts.ready.then(fitBrandTitle);
fitBrandTitle();
