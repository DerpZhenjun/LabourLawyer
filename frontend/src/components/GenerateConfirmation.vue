<template>
  <Teleport to="body">
    <div v-if="open" class="confirm-backdrop" @click.self="$emit('cancel')">
      <section ref="dialog" class="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="generation-title" aria-describedby="generation-description" tabindex="-1">
        <button class="confirm-close" type="button" aria-label="取消生成" @click="$emit('cancel')"><i class="fa-solid fa-xmark" aria-hidden="true"></i></button>
        <span class="confirm-icon"><i class="fa-regular fa-file-word" aria-hidden="true"></i></span>
        <h2 id="generation-title">确认生成{{ documentName }}？</h2>
        <p id="generation-description" v-if="templateOnly">将下载{{ provinceName }}官方空白{{ documentName }}模板，不会带入示例或你已填写的信息。你的填写草稿仍会保留。</p>
        <p id="generation-description" v-else-if="missingFields.length">还有 {{ missingFields.length }} 项内容未填写，仍可生成{{ provinceName }}官方格式文档。空白处可以在 Word 中继续填写。</p>
        <p id="generation-description" v-else>确认后将生成并下载{{ provinceName }}官方格式 Word 文档。请核对内容后再签字提交。</p>
        <div v-if="missingFields.length" class="missing-preview"><i class="fa-solid fa-circle-info" aria-hidden="true"></i><span>{{ missingFields.slice(0,5).join('、') }}<template v-if="missingFields.length>5">等</template></span></div>
        <div class="confirm-actions"><button type="button" class="cancel-button" @click="$emit('cancel')">取消</button><button type="button" class="confirm-button" @click="$emit('confirm')"><i class="fa-solid fa-download" aria-hidden="true"></i> 确认生成</button></div>
      </section>
    </div>
  </Teleport>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useDialogFocus } from '@/composables/useDialogFocus'
const props=withDefaults(defineProps<{open?:boolean;documentName?:string;provinceName?:string;templateOnly?:boolean;missingFields?:string[]}>(),{open:false,templateOnly:false,missingFields:()=>[]})
const emit=defineEmits<{confirm:[];cancel:[]}>()
const dialog=ref<HTMLElement|null>(null)
useDialogFocus(()=>props.open,dialog,()=>emit('cancel'))
</script>
