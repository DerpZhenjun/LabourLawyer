import assert from 'node:assert/strict'
import {resolveAssistantDock} from '../frontend/src/data/assistantDockGeometry.js'
const overlaps=(a,b)=>a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top
for(const width of [375,768,1440]){
 const height=850,size={width:155,height:52},edge=width<=700?16:24
 const action={left:width-310,right:width-20,top:800,bottom:850}
 const result=resolveAssistantDock({width,height},size,[action],edge)
 const box={left:width-result.right-size.width,right:width-result.right,top:height-result.bottom-size.height,bottom:height-result.bottom}
 assert(!result.hidden);assert(!overlaps(box,action),'Floating advice must not cover the mandatory action at '+width)
 assert(box.left>=0&&box.top>=0&&box.right<=width&&box.bottom<=height)
 const normal=resolveAssistantDock({width,height},size,[],edge)
 assert.deepEqual(normal,{right:edge,bottom:edge,hidden:false})
}
const hidden=resolveAssistantDock({width:375,height:500},{width:155,height:52},[{left:0,right:375,top:0,bottom:500}],16)
assert(hidden.hidden,'An unavoidable full-screen primary action takes priority')
console.log('PASS assistant dock: 375/768/1440 primary action clearance, normal position and bounded fallback')
