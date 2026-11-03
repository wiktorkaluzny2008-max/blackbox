// Run with: node test_account_ui.cjs
const fs=require('node:fs');const vm=require('node:vm');const assert=require('node:assert/strict');
const src=fs.readFileSync(require('node:path').join(__dirname,'app_user.py'),'utf8');
const flow=src.slice(src.indexOf('async function loadMe(){'),src.indexOf('function renderMe(r){'));
const ensure=src.slice(src.indexOf('async function ensureAccountPage(){'),src.indexOf('/* ---------- historical analog'));
(async()=>{for(const scenario of ['stale-empty','stale-previous','empty','outage','guest']){
 const body={innerHTML:''};
 const context={ME:{signed_in:true,portfolio:scenario==='stale-previous'?{uid:'old'}:null},ACTIVE_LANG:'en',$:()=>body,pageFromPath:()=> 'account',uid:()=>scenario==='guest'?'guest-id':null,localStorage:{removeItem(){}},renderAuth(){},renderMe(p){context.rendered=p},showEmptyPortfolio(){context.empty=true},fetch:async()=>{if(scenario==='outage')throw Error('offline');return {ok:true,json:async()=>scenario==='empty'?{signed_in:true,portfolio:null}:scenario==='guest'?{signed_in:false,uid:'guest-id'}:{signed_in:true,portfolio:{uid:'saved-new'}}}}};
 vm.createContext(context);vm.runInContext(flow+'\n'+ensure,context);await vm.runInContext('ensureAccountPage()',context);
 if(scenario.startsWith('stale'))assert.equal(context.rendered.uid,'saved-new');
 if(scenario==='empty')assert.equal(context.empty,true);
 if(scenario==='outage'){assert.ok(body.innerHTML.includes('Try again'));assert.ok(!context.empty)}
 if(scenario==='guest')assert.equal(context.rendered.uid,'guest-id');
 console.log(scenario+': passed');
}})().catch(e=>{console.error(e);process.exitCode=1});
