/** Keep optional advice clear of visible form submission controls. */
export function resolveAssistantDock(viewport,size,targets,edge=24,gap=12){
  const {width,height}=viewport
  const visible=targets.filter(t=>t.right>0&&t.left<width&&t.bottom>0&&t.top<height&&t.right>t.left&&t.bottom>t.top)
  const intersects=(a,b)=>a.left<b.right+gap&&a.right>b.left-gap&&a.top<b.bottom+gap&&a.bottom>b.top-gap
  const candidates=[{right:edge,bottom:edge},...visible.flatMap(t=>[
    {right:edge,bottom:height-t.top+gap},
    {right:width-t.left+gap,bottom:edge},
  ])]
  for(const position of candidates){
    const box={left:width-position.right-size.width,right:width-position.right,
      top:height-position.bottom-size.height,bottom:height-position.bottom}
    if(box.left>=edge&&box.top>=edge&&box.right<=width-edge&&box.bottom<=height-edge&&!visible.some(t=>intersects(box,t))){
      return {...position,hidden:false}
    }
  }
  return {right:edge,bottom:edge,hidden:true}
}
