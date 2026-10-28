import {api,t,esc,name,icon} from './shared.js';
let resources=[];
export async function loadResources(){resources=(await api('/api/resources')).resources;renderResources();}
export function renderResources(){
 const tutorials=document.getElementById('tutorial-list'),tools=document.getElementById('tool-list');if(!tutorials||!tools)return;
 tutorials.innerHTML=resources.filter(r=>r.kind==='tutorial').map(r=>`<article class="tutorial-card"><video controls preload="metadata" playsinline aria-label="${esc(name(r.title))}"><source src="${esc(r.video_url)}" type="${esc(r.video_mime)}"></video><div class="resource-body"><h3>${esc(name(r.title))}</h3><p>${esc(name(r.description))}</p></div></article>`).join('')||`<p class="resource-empty">${esc(t('noTutorials'))}</p>`;
 tools.innerHTML=resources.filter(r=>r.kind==='tool').map(r=>`<article class="tool-card"><span class="tool-symbol">${icon('work')}</span><div class="grow"><h3>${esc(name(r.title))}</h3><p>${esc(name(r.description))}</p></div><a class="button secondary" href="${esc(r.download_url)}" target="_blank" rel="noopener noreferrer">${esc(t('download'))}${icon('arrow')}</a></article>`).join('')||`<p class="resource-empty">${esc(t('noTools'))}</p>`;
}
