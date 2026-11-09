import React, {useEffect, useState} from 'react';
import Markdown from 'react-markdown';
async function request(url, options = {}) {
  const response = await fetch(url, {credentials:'same-origin', ...options});
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw Error(typeof body.detail === 'string' ? body.detail : 'Unable to reach the data assistant. Please try again.');
  return body;
}
function Evidence({rows}) {
  if (!rows?.length) return null;
  const columns = [...new Set(rows.flatMap(row => Object.keys(row)))];
  return <details><summary>Supporting Executive ERP calculations</summary><div className="table-scroll"><table><thead><tr>{columns.map(column => <th key={column}>{column}</th>)}</tr></thead><tbody>{rows.map((row,i) => <tr key={i}>{columns.map(column => <td key={column}>{row[column] == null ? 'Unavailable' : String(row[column])}</td>)}</tr>)}</tbody></table></div></details>;
}
export default function ExecutiveChat({filters: suppliedFilters}) {
  const [ownFilters,setOwnFilters] = useState({date:'',period:'mtd',category:'',location:'',start_date:''});
  const filters=suppliedFilters || ownFilters, key=JSON.stringify(filters);
  const [metadata,setMetadata]=useState(null),[messages,setMessages]=useState([]),[question,setQuestion]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false),[ready,setReady]=useState(false),[reload,setReload]=useState(0);
  useEffect(() => {
    const controller=new AbortController(); setReady(false); setMessages([]); setError(''); setQuestion('');
    request(`/api/executive/chat?${new URLSearchParams(Object.entries(filters).filter(([,value])=>value))}`,{signal:controller.signal})
      .then(result=>{setMetadata(result);setMessages(result.messages);setReady(true);})
      .catch(e=>{if(e.name!=='AbortError')setError(e.message);});
    return ()=>controller.abort();
  },[key,reload]);
  async function send(event, text=question) {
    event.preventDefault(); if(!text.trim() || busy || !ready)return;
    setBusy(true);setError('');
    try {
      const reply=await request('/api/executive/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...filters,question:text})});
      setMessages(previous=>[...previous,{role:'user',content:text},{role:'assistant',content:reply.answer,reply}]);setQuestion('');
    } catch(e) {setError(e.message);} finally {setBusy(false);}
  }
  async function clear() {
    setBusy(true);setError('');try{await request('/api/executive/chat',{method:'DELETE'});setMessages([]);}catch(e){setError(e.message);}finally{setBusy(false);}
  }
  function change(name,value) {setOwnFilters(previous=>({...previous,[name]:value,...(name==='period' && value==='custom' && !previous.start_date ? {start_date:(previous.date||metadata.context.as_of).slice(0,7)+'-01'}:{})}));}
  return <section className="panel executive-chat" aria-label="Ask Executive Data">
    <h2>Ask your Executive Data</h2><p>Ask about sales, customers, SKUs, gross profit, margins, trends or plans. Answers use the same ERP extracts as the Executive Dashboard.</p>
    {!suppliedFilters && metadata && <div className="executive-filter-grid"><label>As-of date<input type="date" disabled={busy} min={metadata.min_date} max={metadata.max_date} value={ownFilters.date||metadata.context.as_of} onChange={e=>change('date',e.target.value)}/></label><label>Analysis period<select aria-label="Chat analysis period" disabled={busy} value={ownFilters.period} onChange={e=>change('period',e.target.value)}>{[['day','Selected day'],['mtd','Month to date'],['qtd','Quarter to date'],['ytd','Year to date'],['custom','Custom range']].map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>{ownFilters.period==='custom' && <label>From date<input type="date" disabled={busy} min={metadata.min_date} max={ownFilters.date||metadata.context.as_of} value={ownFilters.start_date} onChange={e=>change('start_date',e.target.value)}/></label>}{['category','location'].map(name=><label key={name}>{name}<select aria-label={`Chat ${name}`} disabled={busy} value={ownFilters[name]} onChange={e=>change(name,e.target.value)}><option value="">All</option>{metadata[name==='category'?'categories':'locations'].map(value=><option key={value}>{value}</option>)}</select></label>)}</div>}
    {metadata && <p className="footnote">{metadata.context.data_source} - AED - {metadata.context.analysis_start} to {metadata.context.analysis_end} - {metadata.context.category||'All categories'} - {metadata.context.location||'All locations'}. Questions may explicitly request another period or filter. Changing filters resets this conversation.</p>}
    {error && <div className="alert error" role="alert">{error}{!ready && <button type="button" className="button secondary" onClick={()=>setReload(value=>value+1)}>Retry connection</button>}</div>}
    {!ready && !error && <p role="status">Connecting to Executive ERP data...</p>}
    <div className="executive-chat-messages" aria-live="polite">{messages.map((message,index)=><article className="executive-chat-message" key={index}><strong>{message.role==='user'?'You':'Executive data analyst'}</strong><Markdown>{message.content}</Markdown>{message.reply?.limitation && <p>{message.reply.limitation}</p>}{message.reply?.source_ids?.length>0 && <p className="footnote">Sources: {message.reply.source_ids.join(', ')}</p>}<Evidence rows={message.reply?.evidence}/></article>)}</div>
    <form className="chat-input" onSubmit={send}><label className="sr-only" htmlFor="executive-question">Question about Executive data</label><input id="executive-question" disabled={!ready||busy} maxLength={4000} value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Which 10 customers generated the most gross profit?"/><button className="button primary" disabled={!ready||busy||!question.trim()}>{busy?'Checking data...':'Ask'}</button></form>
    <div className="suggestions">{['Who are the top 10 customers by gross profit?','What are the bottom 10 SKUs by gross margin?','How does YTD revenue compare with the same period in 2025?','How is revenue tracking against budget and forecast?'].map(text=><button type="button" key={text} disabled={!ready||busy} onClick={event=>send(event,text)}>{text}</button>)}</div>
    <button className="button secondary" type="button" disabled={!ready||busy} onClick={clear}>Clear Executive chat</button>
    <p className="footnote">Relevant calculated ERP results, customer/SKU names, selected filters and recent chat messages are sent to OpenAI when you ask a question. AI must be enabled and a server-side API key configured. Customer-level plans and net profit are unavailable.</p>
  </section>;
}
