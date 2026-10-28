// Original vector illustrations: architecture, flowers and food, not government logos.
import fs from 'node:fs'
import path from 'node:path'
const root=path.resolve(import.meta.dirname,'..')
const entries=[
 ['beijing','京城屋檐','宫殿','#9e463b','#fcf0e6',0],['tianjin','海河桥影','桥梁','#32688b','#edf5fa',1],
 ['hebei','长城山色','长城','#736244','#f7f3e9',2],['shanxi','晋地古塔','古塔','#8b603e','#faf2e7',3],
 ['neimenggu','草原毡房','毡房','#457660','#edf6ef',4],['liaoning','盛京红墙','宫殿','#985348','#faefea',5],
 ['jilin','长白山与雪','山峰','#386978','#edf6f8',6],['heilongjiang','冰城穹顶','穹顶','#586c9f','#f0f3fb',7],
 ['shanghai','浦江天际线','高楼','#5063a0','#eff2fb',8],['jiangsu','江南园林','园林','#45796a','#eff7f3',9],
 ['zhejiang','西湖荷影','荷花','#317b78','#ecf8f5',10],['anhui','徽州白墙','徽派','#586575','#f2f4f6',11],
 ['fujian','闽地土楼','土楼','#9a6845','#fbf3e8',12],['jiangxi','瓷与山水','瓷器','#496d9b','#f0f5fc',13],
 ['shandong','岱岳松影','山峰','#597145','#f2f6eb',14],['henan','古都牡丹','花卉','#966276','#fcf0f4',15],
 ['hubei','江城楼阁','古塔','#94713b','#faf5e9',16],['hunan','湘江楼影','古塔','#8a6349','#fbf3ec',17],
 ['guangdong','木棉与岭南','花卉','#ad5d41','#fff2e8',18],['guangxi','桂林山水','山峰','#467e78','#eff8f5',19],
 ['hainan','椰风海岸','椰树','#287c91','#eef9fb',20],['chongqing','山城桥影','桥梁','#986049','#fbf1eb',21],
 ['sichuan','竹林茶香','茶碗','#647c48','#f3f7eb',22],['guizhou','黔地鼓楼','古塔','#63748a','#f1f5f9',23],
 ['yunnan','山茶花开','花卉','#a65869','#fbf0f3',24],['xizang','雪域宫墙','宫殿','#845f54','#faf3ec',25],
 ['shaanxi','长安城楼','宫殿','#8e664c','#f9f2e8',26],['gansu','敦煌沙色','沙丘','#ab773c','#fdf5e5',27],
 ['qinghai','青海湖波','湖泊','#41779d','#eef6fc',28],['ningxia','塞上枸杞','花卉','#8f624c','#f9f2ec',29],
 ['xinjiang','天山果香','果盘','#728044','#f7f8eb',30],
]
const motifs={
 '宫殿':i=>`<path d="M100 200V120H270V200M85 120L185 ${65-i%3*7}L285 120Z"/><path d="M130 120V195M162 120V195M203 120V195M238 120V195"/><path d="M165 200V156Q185 139 205 156V200"/>`,
 '桥梁':i=>`<path d="M65 172H305M75 175Q185 ${25+i%3*8} 295 175M93 154V176M125 113V176M158 91V176M210 89V176M245 110V176M277 150V176"/><path d="M90 198Q120 190 150 198T210 198T270 198"/>`,
 '长城':()=>`<path d="M60 200L100 155L135 162L175 115L213 126L252 85L306 101V127L259 110L220 153L184 141L145 185L106 179L74 214Z"/><path d="M167 125V99H194V129M245 95V67H272V103"/>`,
 '古塔':i=>`<path d="M137 200V164H232V200M147 161V127H222V161M159 125V92H210V125M171 90V67H199V90"/><path d="M122 163L185 135L247 163M132 127L185 102L237 127M144 92L185 ${58+i%4*2}L223 92M157 66L185 47L214 66"/>`,
 '毡房':()=>`<path d="M96 189V135Q184 43 274 135V189ZM96 136H274M162 189V150Q185 134 207 150V189"/><path d="M78 206Q154 183 291 204"/>`,
 '山峰':i=>`<path d="M52 210L125 ${60+i%3*10}L183 155L229 ${42+i%5*4}L318 210M96 120L124 99L148 123M202 98L228 76L247 101"/>`,
 '穹顶':()=>`<path d="M117 200V119H255V200M146 118V90Q184 19 225 90V118M178 57V35M105 118H267M147 196V156M187 196V145M229 196V156"/>`,
 '高楼':()=>`<path d="M88 200V108H127V200M152 200V95L170 65V95H190V200M218 200V74H244V200M231 74V40M270 200V131H298V200"/><circle cx="177" cy="124" r="18"/>`,
 '园林':()=>`<path d="M102 196V129H268V196M86 130Q133 123 183 86Q225 123 284 130M124 132V187M247 132V187M146 196Q184 126 222 196M64 208Q184 192 306 208"/>`,
 '荷花':()=>`<path d="M185 206V139M185 146Q115 162 129 99Q177 105 185 146M185 146Q232 107 240 151Q213 162 185 146M185 139Q142 94 163 63Q190 69 185 139M185 139Q233 102 215 67Q184 79 185 139"/><ellipse cx="175" cy="210" rx="90" ry="13"/>`,
 '徽派':()=>`<path d="M84 199V136L126 105L167 136V200M166 200V146L214 111L268 146V200M82 137L126 91L170 137M165 145L214 97L272 145M105 198V159H140V198M189 166H214V188H189Z"/>`,
 '土楼':()=>`<ellipse cx="184" cy="111" rx="101" ry="40"/><path d="M83 110V170Q182 235 285 170V110M118 133V187M153 149V203M215 149V203M254 133V187"/><ellipse cx="184" cy="111" rx="54" ry="18"/>`,
 '瓷器':()=>`<path d="M154 59H214V91Q270 117 249 185Q230 218 141 206Q111 200 113 165Q112 116 154 91ZM149 70H218M127 151Q184 121 247 155M145 173Q167 145 197 178Q219 192 236 171"/>`,
 '椰树':()=>`<path d="M177 207Q205 141 189 93M189 95Q153 52 112 70M189 95Q224 44 278 77M189 95Q254 76 286 116M189 95Q151 93 112 141M76 213Q159 193 284 212"/>`,
 '茶碗':()=>`<path d="M112 140H255Q251 203 185 203Q121 196 112 140ZM98 208H269M140 125Q124 108 148 88M180 123Q165 100 188 74M218 123Q202 104 225 87"/>`,
 '沙丘':()=>`<path d="M44 189Q135 99 218 170Q271 205 330 152M45 218Q170 134 303 221M126 173V107M109 110L127 80L146 110M130 189V155H175V202"/>`,
 '湖泊':()=>`<path d="M43 142L107 88L163 128L233 65L318 142M66 168Q104 152 146 168T227 168T301 168M90 196Q128 182 169 196T247 196M118 222Q168 207 231 222"/>`,
 '果盘':()=>`<path d="M90 172H277Q259 211 184 211Q112 208 90 172"/><circle cx="153" cy="137" r="26"/><circle cx="208" cy="136" r="26"/><circle cx="182" cy="103" r="23"/><path d="M180 78Q192 55 213 64"/>`,
 '花卉':i=>Array.from({length:5+i%3},(_,n)=>`<ellipse cx="184" cy="92" rx="18" ry="36" transform="rotate(${n*360/(5+i%3)} 184 128)"/>`).join('')+`<circle cx="184" cy="128" r="17"/><path d="M184 151V219Q140 202 131 164Q170 167 184 198M184 201Q224 157 249 165Q234 204 184 217"/>`,
}
const themes={}
fs.mkdirSync(path.join(root,'frontend/public/province-art'),{recursive:true})
for(const [slug,motif,kind,accent,wash,i] of entries){
 themes[slug]={motif,kind,accent,wash,art:`/province-art/${slug}.svg`,miniArt:`/assets/province-art/${slug}.png`}
 const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="380" height="260" viewBox="0 0 380 260"><rect width="380" height="260" rx="32" fill="${wash}"/><circle cx="${284-i%5*7}" cy="64" r="32" fill="${accent}" opacity=".12"/><path d="M0 222Q90 ${175+i%7*3} 180 216T380 213V260H0Z" fill="${accent}" opacity=".08"/><g fill="${wash}" stroke="${accent}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">${motifs[kind](i)}</g><g fill="${accent}" opacity=".25"><circle cx="63" cy="83" r="3"/><circle cx="312" cy="137" r="5"/><circle cx="${50+i*3}" cy="38" r="2"/></g></svg>`
 fs.writeFileSync(path.join(root,`frontend/public/province-art/${slug}.svg`),svg)
}
fs.writeFileSync(path.join(root,'config/province_themes.json'),JSON.stringify(themes,null,2)+'\n')
console.log(`Created ${entries.length} original province illustrations`)
