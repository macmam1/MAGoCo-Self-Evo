/**
 * Feature Manifest Schema
 * هر ماژول باید یک manifest.json داشته باشد
 */

export interface FeatureManifest {
  /** شناسه منحصر به فرد (مثال: chat-core، browser-agent، workflow-engine) */
  id: string;
  /** نام نمایشی */
  name: string;
  /** توضیح کوتاه */
  description: string;
  /** نسخه (semver) */
  version: string;
  /** نویسنده/تیم */
  author?: string;
  /** پیش‌نیازها (feature idهای دیگر) */
  dependencies?: string[];
  /** دسته‌بندی برای UI */
  category: "core" | "chat" | "browser" | "workflow" | "memory" | "skills" | "integrations" | "settings" | "developer";
  /** اولویت بارگذاری (بالاتر = زودتر لود میشه) */
  priority: number;
  /** آیا به طور پیش‌فرض فعال باشد؟ */
  enabledByDefault: boolean;
  /** حداقل نسخه هسته مورد نیاز */
  minCoreVersion?: string;
  /** نقاط ورود (entry points) */
  entryPoints: {
    /** کامپوننت اصلی UI */
    main?: string;
    /** تنظیمات */
    settings?: string;
    /** کامپوننت‌های اضافه */
    components?: Record<string, string>;
  };
  /** مجوزهای مورد نیاز */
  permissions?: string[];
  /** متادیتای توسعه‌دهنده */
  meta?: {
    tags?: string[];
    icon?: string;
    color?: string;
    docsUrl?: string;
    repoUrl?: string;
  };
}

export interface FeatureConfig {
  /** آیا ویژگی فعال است؟ */
  enabled: boolean;
  /** تنظیمات خاص کاربر */
  userConfig?: Record<string, unknown>;
  /** آخرین بروزرسانی */
  updatedAt: string;
}

/** وضعیت کامل یک ویژگی در runtime */
export interface FeatureState extends FeatureManifest {
  config: FeatureConfig;
  status: "unloaded" | "loading" | "loaded" | "error" | "disabled";
  error?: string;
  loadedAt?: string;
}