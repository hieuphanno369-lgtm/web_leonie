/**
 * messages.ts — Kho thông điệp tiếng Việt dùng chung cho toàn app.
 *
 * Mục tiêu: mọi thông báo lỗi, empty-state, nhắc nhập liệu và trạng thái mà
 * NGƯỜI DÙNG nhìn thấy đều gom về một chỗ, viết bằng tiếng Việt thân thiện,
 * tránh thuật ngữ kỹ thuật. Khi cần đổi chữ chỉ sửa ở đây.
 *
 * Quy ước: dùng `MSG.<key>`. Một vài key là hàm để chèn số liệu.
 */
export const MSG = {
  // ── Kết nối / lỗi chung ──────────────────────────────────────────────
  apiUnreachable: 'Không kết nối được tới máy chủ. Hãy đảm bảo ứng dụng đang chạy rồi thử lại.',
  saveFailed:     'Lưu thất bại. Kiểm tra kết nối rồi thử lại.',
  deleteFailed:   'Xóa thất bại. Kiểm tra kết nối rồi thử lại.',
  updateFailed:   'Cập nhật thất bại. Vui lòng thử lại.',
  loadFailed:     'Tải dữ liệu thất bại.',
  queryFailed:    'Truy vấn thất bại.',

  // ── Trạng thái đang xử lý ────────────────────────────────────────────
  loading:        'Đang tải…',
  loadingTables:  'Đang tải bảng…',
  saving:         'Đang lưu…',

  // ── Tải / lưu cụ thể theo tính năng ──────────────────────────────────
  loadTasksFailed:       'Tải danh sách task thất bại.',
  loadCorrelationFailed: 'Tải tương quan thất bại.',
  loadJobsFailed:        'Tải danh sách công việc thất bại.',
  loadCodeFailed:        'Tải mã nguồn thất bại.',
  saveRuleFailed:        'Lưu quy tắc thất bại.',
  saveSettingsFailed:    'Lưu cài đặt thất bại.',
  saveNoteFailed:        'Lưu ghi chú thất bại.',
  saveJobFailed:         'Lưu công việc thất bại.',
  createWipFailed:       'Tạo WIP thất bại. Kiểm tra kết nối rồi thử lại.',
  updateProgressFailed:  'Cập nhật tiến độ thất bại.',
  addLogFailed:          'Thêm nhật ký thất bại.',
  deleteLogFailed:       'Xóa nhật ký thất bại.',
  deleteJobFailed:       'Xóa công việc thất bại.',
  pollStatusFailed:      'Không lấy được trạng thái công việc.',
  previewFailed:         'Xem trước thất bại.',
  runFailed:             'Chạy thất bại.',
  checkFailed:           'Kiểm tra thất bại.',
  uploadFailed:          'Tải tệp lên thất bại — kiểm tra định dạng hoặc dung lượng tệp.',
  testWebhookFailed:     'Gửi thử thất bại — kiểm tra lại Webhook URL.',
  sendWebhookFailed:     'Gửi thất bại — kiểm tra lại Webhook URL.',
  cohortFailed:          'Phân tích cohort thất bại.',
  timeseriesFailed:      'Phân tích chuỗi thời gian thất bại.',
  forecastFailed:        'Dự báo thất bại.',
  compareFailed:         'So sánh thất bại.',
  aiExplainFailed:       'AI giải thích thất bại.',
  statsFailed:           'Phân tích thống kê thất bại.',
  aiInterpretFailed:     'AI diễn giải thất bại.',
  drilldownFailed:       'Khoan sâu dữ liệu thất bại.',
  requestFailed:         'Yêu cầu thất bại.',
  enterDirFirst:         'Hãy nhập thư mục trước.',
  verifyPathFailed:      'Không kiểm tra được đường dẫn (lỗi máy chủ).',

  // ── Chất lượng dữ liệu (Data Quality banner) ─────────────────────────
  qualityCheckFailed: 'Kiểm tra chất lượng dữ liệu thất bại.',
  qualityNoIssues:    'Không phát hiện vấn đề chất lượng dữ liệu.',
  qualityIssuesFound: (n: number) => `Phát hiện ${n} vấn đề chất lượng dữ liệu`,

  // ── Nhắc nhập liệu (validation) ──────────────────────────────────────
  titleRequired:        'Vui lòng nhập tiêu đề.',
  requesterRequired:    'Vui lòng nhập người yêu cầu.',
  datasetRequired:      'Vui lòng nhập tên dữ liệu.',
  requesterRequiredEda: 'EDA cần có người yêu cầu.',
  datasetRequiredEda:   'EDA cần có tên dữ liệu.',
  metricRequired:       'Vui lòng nhập tên chỉ số.',
  validNumberRequired:  'Vui lòng nhập một số hợp lệ.',
  contentRequired:      'Vui lòng nhập nội dung.',
  dateRequired:         'Vui lòng chọn ngày.',
  selectTaskRequired:   'Vui lòng chọn một task.',
  jobNameRequired:      'Vui lòng nhập tên công việc.',
  exportFormatRequired: 'Chọn ít nhất một định dạng xuất.',
  exportDirRequired:    'Vui lòng nhập thư mục đích để xuất.',
  soqlRequired:         'Vui lòng nhập câu truy vấn SOQL.',
  objectNameRequired:   'Vui lòng nhập tên đối tượng (Object).',
  sourceUrlRequired:    'Vui lòng nhập URL nguồn.',
  messageEmpty:         'Nội dung tin nhắn đang trống.',
  setWebhookFirst:      'Hãy đặt Webhook URL trong tab Cài đặt trước.',
  enterWebhookFirst:    'Hãy nhập Webhook URL trước.',

  // ── Trạng thái thành công ────────────────────────────────────────────
  sent:     'Đã gửi! ✓',
  saved:    'Đã lưu! ✓',
  testSent: 'Đã gửi thử! ✓',
  checkDone: (n: number) => `Đã kiểm tra — đã gửi ${n} thông báo.`,

  // ── Hộp thoại xác nhận ───────────────────────────────────────────────
  confirmDelete: (what: string) => `Xóa ${what}? Thao tác này không thể hoàn tác.`,

  // ── Empty states (chưa có dữ liệu) ───────────────────────────────────
  emptySelectTask: 'Chọn một task hoặc tạo mới',
  emptySelectWip:  'Chọn một WIP hoặc tạo mới',
  emptySelectPlan: 'Chọn một kế hoạch hoặc tạo mới',
  emptySelectNote: 'Chọn một ghi chú hoặc tạo mới',
  emptySelectEda:  'Chọn một yêu cầu hoặc tạo mới',
  emptySelectJob:  'Chọn một công việc, hoặc bấm "New" để tạo mới.',
  emptyWipList:    'Chưa có WIP nào',
  emptyEdaRequests: 'Chưa có yêu cầu EDA nào',
  emptyJobList:    'Chưa có công việc nào — bấm "New".',
  emptySnippets:     'Chưa có snippet nào',
  emptySnippetsHint: 'Bấm "New Snippet" để lưu câu SQL đầu tiên.',
  emptyViews:        'Chưa có view nào',
  emptyViewsHint:    'Bấm "New View" để thêm định nghĩa Fabric view.',
  emptyHistory:    'Chưa có lịch sử truy vấn.',
  emptyLogs:       'Chưa có nhật ký nào',
  emptyDatasets:   'Chưa có dữ liệu. Hãy nạp VINA BREW hoặc tải lên tệp CSV/Excel.',
  runToSeeResults: 'Chạy truy vấn để xem kết quả',
  runToSeeCharts:  'Chạy truy vấn để xem biểu đồ',
  cohortRunAllHint: 'Bấm "Run All" để tính.',
  mlUploadHint:    'Tải lên tệp CSV hoặc Excel để khám phá, trực quan hóa và dự báo dữ liệu — không cần viết code.',
  placeholderMessage: 'Nhập nội dung thông báo...',
} as const
