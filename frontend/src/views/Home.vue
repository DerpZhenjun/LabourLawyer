<template>
  <div class="home-page">
    
    <QA @open-digital-human="showDigitalLawyer = true" />

    <div class="content-wrapper">
      <div class="container search-section">
        <div class="row justify-content-center">
          <div class="col-md-10 col-lg-7">
            <div class="search-container animate__animated animate__fadeInDown">
              <form @submit.prevent="handleSearch" class="modern-search-form">
                <i class="fas fa-search search-icon"></i>
                <input 
                  type="text" 
                  class="modern-input" 
                  v-model="searchQuery" 
                  placeholder="搜索文书 (如: 劳动仲裁、证据清单...)"
                  @focus="isFocused = true"
                  @blur="isFocused = false"
                >
                <button type="submit" class="modern-search-btn">
                  搜索
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>

      <div id="main" class="container mt-4 pb-5">
        
        <div class="section-header text-center mb-5 animate__animated animate__fadeIn">
          <h1 class="main-title">
            <span class="icon-box"><i class="fas fa-gavel"></i></span>
            <span class="text">劳动仲裁</span>
          </h1>
          <p class="subtitle">选择您所在的省份，快速生成专业法律文书</p>
        </div>

        <div class="row g-4">
          <div v-for="(prov, index) in provinces" :key="index" class="col-md-6 col-lg-4">
            <div class="glass-card h-100">
              <div class="card-body d-flex justify-content-around align-items-center py-4">
                
                <div class="action-item" @click="navigateTo(prov.laRoute)">
                  <div class="icon-circle mb-3">
                    <img :src="getImageUrl(prov.laImg)" :alt="prov.name + '仲裁申请'">
                  </div>
                  <h6 class="action-text">仲裁申请</h6>
                </div>
                
                <div class="divider-line"></div>

                <div class="action-item" @click="navigateTo(prov.elRoute)">
                  <div class="icon-circle mb-3">
                    <img :src="getImageUrl(prov.elImg)" :alt="prov.name + '证据清单'">
                  </div>
                  <h6 class="action-text">证据清单</h6>
                </div>

              </div>
              
              <div class="card-footer-custom">
                <div class="province-name">{{ prov.name }}</div>
                <div class="source-link">
                  <i class="fas fa-link me-1"></i>
                  <a :href="prov.sourceUrl" target="_blank">{{ prov.sourceName }}</a>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>

    <transition name="fade-slide">
      <DigitalLawyer 
        v-if="showDigitalLawyer" 
        @close="showDigitalLawyer = false" 
      />
    </transition>

  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';

// 引入组件
import QA from '@/components/QA.vue';
import DigitalLawyer from '@/components/DigitalLawyer.vue';

const router = useRouter();
const searchQuery = ref('');
const isFocused = ref(false); 

// 控制数字律师显示的变量
const showDigitalLawyer = ref(false);

const provinces = [
  {
    name: '浙江省',
    laRoute: '/zhejiang/la', laImg: 'zj-la.png',
    elRoute: '/zhejiang/el', elImg: 'zj-el.png',
    sourceName: '浙江政务服务网', sourceUrl: 'https://www.zjzwfw.gov.cn/'
  },
  {
    name: '广东省',
    laRoute: '/guangdong/la', laImg: 'gd-la.png',
    elRoute: '/guangdong/el', elImg: 'gd-el.png',
    sourceName: '广东政务服务网', sourceUrl: 'https://www.gdzwfw.gov.cn/'
  },
  {
    name: '江苏省',
    laRoute: '/jiangsu/la', laImg: 'js-la.png',
    elRoute: '/jiangsu/el', elImg: 'js-el.png',
    sourceName: '江苏政务服务网', sourceUrl: '#'
  },
  {
    name: '辽宁省',
    laRoute: '/liaoning/la', laImg: 'ln-la.png',
    elRoute: '/liaoning/el', elImg: 'ln-el.png',
    sourceName: '辽宁政务服务网', sourceUrl: '#'
  },
  {
    name: '福建省',
    laRoute: '/fujian/la', laImg: 'fj-la.png',
    elRoute: '/fujian/el', elImg: 'fj-el.png',
    sourceName: '福建政务服务网', sourceUrl: '#'
  }
];

const getImageUrl = (name:string) => {
  return new URL(`../assets/img/${name}`, import.meta.url).href;
};

const navigateTo = (path:string) => {
  if (path) router.push(path);
  else alert('该功能正在开发中...');
};

const handleSearch = () => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) return;

  const keywordMap:Record<string,string> = {
    '劳动': '/zhejiang/la',
    '仲裁': '/zhejiang/la',
    '申请书': '/zhejiang/la',
    '证据': '/zhejiang/el',
    '清单': '/zhejiang/el',
    '广东': '/guangdong/la',
    '浙江': '/zhejiang/la'
  };

  let targetPath:string|undefined;
  for (const key in keywordMap) {
    if (query.includes(key)) {
      targetPath = keywordMap[key];
      break;
    }
  }

  if (targetPath) {
    router.push(targetPath);
  } else {
    alert('未找到相关文书，请尝试输入：劳动仲裁、证据清单、工伤...');
  }
};
</script>

<style scoped>
/* ======================================================== */
/* 页面基础样式 */
/* ======================================================== */
.home-page {
  position: relative;
  min-height: 100vh;
  width: 100%;
  background-image: url("@/assets/img/index-backgroundimg.png");
  background-position: center;
  background-size: cover;
  background-attachment: fixed;
  background-repeat: no-repeat;
  overflow-x: hidden; 
  display: flex;
  flex-direction: column;
}

.home-page::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(245, 247, 250, 0.3); 
  pointer-events: none; 
  z-index: 0;
}

.content-wrapper {
  position: relative;
  z-index: 1;
  padding-top: 0; 
}

.search-section {
  margin-top: 30px; 
  margin-bottom: 2rem;
}

.search-container {
  position: relative;
  transition: transform 0.3s ease;
}

.modern-search-form {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 8px 8px 8px 25px;
  border-radius: 50px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.5);
  transition: all 0.3s ease;
}

.modern-search-form:focus-within {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(235, 171, 98, 0.25);
  background: #ffffff;
}

.search-icon {
  color: #999;
  font-size: 1.2rem;
  margin-right: 15px;
}

.modern-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 1.1rem;
  color: #333;
  outline: none;
  padding: 10px 0;
}

.modern-input::placeholder {
  color: #aaa;
}

.modern-search-btn {
  background: linear-gradient(135deg, #ebab62, #e69138);
  color: white;
  border: none;
  padding: 12px 35px;
  border-radius: 40px;
  font-weight: 600;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(235, 171, 98, 0.4);
}

.modern-search-btn:hover {
  background: linear-gradient(135deg, #f0b670, #eb9c4d);
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(235, 171, 98, 0.6);
}

.main-title {
  font-weight: 800;
  color: #1a1a1a; 
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  text-shadow: 2px 2px 0px rgba(255, 255, 255, 0.8), 
               0 0 20px rgba(255, 255, 255, 0.5);
}

.icon-box {
  background: linear-gradient(135deg, #ebab62, #ffdaaa);
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 1.5rem;
  box-shadow: 0 4px 10px rgba(235, 171, 98, 0.3);
}

.subtitle {
  font-size: 1.1rem;
  color: #333; 
  font-weight: 600; 
  display: inline-block; 
  background: rgba(255, 255, 255, 0.75); 
  backdrop-filter: blur(4px);
  padding: 8px 25px; 
  border-radius: 50px; 
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
}

.other-title {
  color: #222;
  font-weight: 800;
  position: relative;
  display: inline-block; 
  padding: 0 15px;
  text-shadow: 0 2px 0 rgba(255, 255, 255, 0.9);
}

.other-title::after {
  content: '';
  display: block;
  width: 60px;
  height: 4px;
  background: #ebab62;
  margin: 10px auto 0;
  border-radius: 2px;
}

.glass-card {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 10px 30px rgba(0,0,0,0.05);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  overflow: hidden;
  cursor: default;
}

.glass-card:hover {
  transform: translateY(-8px);
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 20px 40px rgba(0,0,0,0.08);
}

.action-item {
  cursor: pointer;
  text-align: center;
  transition: transform 0.2s;
  padding: 10px;
  border-radius: 15px;
}
.action-item:hover {
  transform: scale(1.05);
  background: rgba(235, 171, 98, 0.05);
}

.icon-circle {
  width: 70px;
  height: 70px;
  background: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
}

.icon-circle img {
  width: 45px;
  height: 45px;
  object-fit: contain;
}

.divider-line {
  width: 1px;
  height: 60px;
  background: linear-gradient(to bottom, transparent, #ddd, transparent);
}

.card-footer-custom {
  background: rgba(248, 249, 250, 0.6);
  padding: 12px;
  text-align: center;
  border-top: 1px solid rgba(0,0,0,0.03);
}

.province-name {
  font-weight: 700;
  color: #444;
  font-size: 1.1rem;
}

.source-link a {
  color: #888;
  text-decoration: none;
  font-size: 0.85rem;
  transition: color 0.2s;
}

.source-link a:hover {
  color: #ebab62;
  text-decoration: underline;
}

.simple-card {
  cursor: pointer;
}
.simple-card:active {
  transform: scale(0.98);
}

/* ======================================================== */
/* DigitalLawyer 组件的入场动画 */
/* ======================================================== */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.4s cubic-bezier(0.19, 1, 0.22, 1);
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}
</style>
