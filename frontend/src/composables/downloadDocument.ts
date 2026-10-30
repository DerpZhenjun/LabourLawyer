import { Capacitor } from '@capacitor/core'
import { Directory, Filesystem } from '@capacitor/filesystem'
import { Share } from '@capacitor/share'

const blobToBase64 = (blob:Blob) => new Promise<string>((resolve, reject) => {
  const reader = new FileReader()
  reader.onerror = () => reject(reader.error || new Error('文件读取失败'))
  reader.onload = () => resolve(String(reader.result).split(',')[1] || '')
  reader.readAsDataURL(blob)
})

export const downloadDocument = async (blob:Blob, filename:string):Promise<void> => {
  if (Capacitor.isNativePlatform()) {
    const safeName = filename.replace(/[\\/:*?"<>|]/g, '_')
    const path = `documents/${Date.now()}-${safeName}`
    await Filesystem.writeFile({
      path,
      data: await blobToBase64(blob),
      directory: Directory.Cache,
      recursive: true,
    })
    const file = await Filesystem.getUri({ path, directory: Directory.Cache })
    await Share.share({
      title: '保存劳动仲裁文书',
      text: '请选择 Word、文件管理器或其他应用保存这份文书。',
      files: [file.uri],
      dialogTitle: '保存或分享文书',
    })
    return
  }

  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
