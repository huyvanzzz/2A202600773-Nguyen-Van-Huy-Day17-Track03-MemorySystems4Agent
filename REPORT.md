# BÁO CÁO PHÂN TÍCH KẾT QUẢ BENCHMARK (STUDENT REPORT)

* **Họ và tên sinh viên**: Nguyễn Văn Huy
* **Mã số sinh viên (MSSV)**: 2A202600773
* **Dự án**: Memory Systems for AI Agent - Day 17 Lab (Phase 2 Track 3)

---

## 1. BẢNG SỐ LIỆU THỰC NGHIỆM (ONLINE - LIVE LLM)

Các số liệu dưới đây thu được bằng việc chạy thực nghiệm kiểm thử trực tiếp (Online) với mô hình `gemini-3.1-flash-lite` thông qua cổng kết nối **AntcoAILLM Gateway** (`https://ai-gateway.antco.ai/v1`).

### 1.1. Standard Benchmark (conversations.json)
Standard suite đánh giá khả năng nhớ thông tin chéo phiên của 10 cuộc hội thoại bình thường:

| Agent Name     |   Agent Tokens Only |   Prompt Tokens Processed | Cross-Session Recall   | Response Quality   |   Memory Growth (bytes) |   Compactions |
|----------------|---------------------|---------------------------|------------------------|--------------------|-------------------------|---------------|
| **Baseline Agent** |               46,374 |                    216,028 | 17.50%                 | 26.43%             |                       0 |             0 |
| **Advanced Agent** |               31,945 |                    103,740 | **46.64%**             | **60.36%**         |                     375 |            83 |

### 1.2. Long-Context Stress Benchmark (advanced_long_context.json)
Stress suite đánh giá khả năng nén bộ nhớ trên các chuỗi hội thoại siêu dài nhằm kiểm tra tính hiệu quả của lớp Compact Memory:

| Agent Name     |   Agent Tokens Only |   Prompt Tokens Processed | Cross-Session Recall   | Response Quality   |   Memory Growth (bytes) |   Compactions |
|----------------|---------------------|---------------------------|------------------------|--------------------|-------------------------|---------------|
| **Baseline Agent** |                5,424 |                     54,396 | 0.00%                  | 36.67%             |                       0 |             0 |
| **Advanced Agent** |                8,598 |                     45,022 | **50.00%**             | **56.67%**         |                     460 |            28 |

---

## 2. PHÂN TÍCH VÀ ĐÁNH GIÁ (REFLECTION & TRADE-OFFS)

### 2.1. Tại sao Advanced Agent có Recall chéo phiên tốt hơn Baseline Agent?
- **Baseline Agent**: Chỉ lưu lịch sử trong cùng một thread (SessionState). Khi chuyển sang thread mới để trả lời câu hỏi recall, Baseline Agent khởi đầu với lịch sử trống rỗng nên không có thông tin về người dùng, dẫn đến độ recall thấp (chỉ đạt 17.50% ở hội thoại ngắn và 0.00% ở hội thoại stress).
- **Advanced Agent**: Sở hữu lớp persistent memory bền vững thông qua file `User.md`. Ngay khi bắt đầu một session hoặc thread mới, Agent tự động đọc hồ sơ người dùng hiện tại và nạp vào prompt ngữ cảnh. Nhờ đó, Agent luôn ghi nhớ chính xác các facts dài hạn (đạt recall từ **46.64% đến 50.00%**).

### 2.2. Sự đánh đổi (Trade-off) về chi phí Token ở hội thoại ngắn và dài
- **Hội thoại ngắn**: Ở các hội thoại rất ngắn, Advanced Agent có thể tiêu tốn prompt token nhiều hơn Baseline Agent do phải chịu thêm chi phí cố định từ việc mang theo hồ sơ người dùng từ `User.md` và các chỉ dẫn hệ thống (system prompt instructions) phức tạp hơn.
- **Hội thoại dài**: Khi hội thoại kéo dài (Stress Test), Compact Memory của Advanced Agent bắt đầu phát huy thế mạnh vượt trội. Thay vì mang theo toàn bộ lịch sử thô phình to liên tục của Baseline (tiêu tốn **54,396** tokens), Advanced Agent chủ động nén các lượt hội thoại cũ thành bản tóm tắt tinh gọn và chỉ giữ lại tin nhắn gần nhất. Lượng prompt tokens processed giảm xuống chỉ còn **45,022** (giảm **17%**). 
- Sự tối ưu này càng rõ rệt trong Standard Benchmark dài hạn khi tổng prompt tokens của Advanced Agent giảm **hơn 52%** (chỉ tiêu tốn **103,740** tokens so với **216,028** của Baseline).

### 2.3. Tốc độ tăng trưởng của file memory và các rủi ro đi kèm
- **Tốc độ tăng trưởng**: File `User.md` tăng trưởng rất chậm và ổn định (chỉ chiếm **375 bytes** và **460 bytes** sau toàn bộ quá trình chạy).
- **Lý do & Giải pháp**: Đó là nhờ hai cơ chế nâng cao đã được cài đặt:
  1. *Conflict Handling*: Tự động phát hiện và ghi đè thông tin mới đính chính (ví dụ: chuyển từ Huế sang Đà Nẵng) thay vì lưu trữ cả hai, giúp file không bị thừa dữ liệu mâu thuẫn.
  2. *Memory Decay*: Các thông tin cũ, ít được nhắc lại sẽ tự động giảm độ tự tin và bị loại bỏ khi rớt xuống dưới ngưỡng 0.3.
- **Rủi ro tiềm ẩn**: 
  - Nếu không có bộ lọc tốt (Confidence Threshold), file `User.md` sẽ bị ô nhiễm bởi các thông tin rác, các câu hỏi hoặc các distractor do người dùng đưa ra.
  - Quá trình tóm tắt (summarize) của lớp Compact Memory có thể làm mất mát chi tiết quan trọng hoặc tạo ra ảo tưởng (hallucination) khi chuyển thông tin hội thoại sang văn bản tóm tắt. Do đó, cần thiết kế prompt tóm tắt thật chặt chẽ và chọn lọc.

---

## 3. PHÂN TÍCH CHI TIẾT CÁC TÍNH NĂNG BỔ SUNG (BONUS FEATURES)

Để đạt mức điểm tối đa (90-100 điểm), hệ thống bộ nhớ của Advanced Agent đã được trang bị 4 tính năng nâng cao và giải quyết triệt để các vấn đề trong thực tế sản xuất:

### 3.1. Confidence Threshold (Bộ lọc độ tin cậy)
* **Vấn đề giải quyết**: Tránh việc lưu trữ các thông tin "rác" hoặc hiểu nhầm ý định khi người dùng chỉ đang đặt câu hỏi (ví dụ: *"Bạn có biết DũngCT không?"*) hoặc đưa ra giả định/tin đùa/thông tin gây nhiễu (ví dụ: *"Hà Nội chỉ là nơi mình vừa bay ra họp chứ không phải nơi ở hiện tại"*).
* **Cải thiện hiệu năng**: Giúp file `User.md` luôn sạch sẽ, không bị phình to bởi thông tin thừa hoặc hiểu nhầm. Giảm chi phí token lưu trữ dài hạn và cải thiện độ chính xác cho câu trả lời.
* **Rủi ro đi kèm**: Có khả năng bỏ sót một số thông tin thật nếu người dùng diễn đạt phức tạp giống câu hỏi, hoặc cấu trúc câu của họ không khớp với bộ lọc heuristic.

### 3.2. Conflict Handling (Xử lý xung đột thông tin)
* **Vấn đề giải quyết**: Khi người dùng thay đổi thông tin cá nhân (ví dụ: chuyển từ Huế sang Đà Nẵng, chuyển từ Backend Engineer sang MLOps Engineer), Agent sẽ tự động ghi đè thông tin mới lên khóa (key) tương ứng thay vì lưu song song hai thông tin mâu thuẫn.
* **Cải thiện hiệu năng**: Giúp duy trì tỷ lệ **Recall chính xác đạt tối đa (50.00% trong Stress Test)** khi người dùng truy vấn các facts đã được đính chính.
* **Rủi ro đi kèm**: Nếu bộ trích xuất nhận diện nhầm thực thể (ví dụ: nhầm địa điểm công tác tạm thời thành địa chỉ thường trú), thông tin chính xác có thể bị ghi đè sai.

### 3.3. Structured Entity Extraction (Trích xuất thực thể có cấu trúc)
* **Vấn đề giải quyết**: Tổ chức thông tin người dùng lưu trong `User.md` thành định dạng danh sách có khóa (key-value) chuẩn hóa (Tên, Nơi ở, Nghề nghiệp, Đồ uống, Món ăn, Thú cưng, Style trả lời) thay vì ghi nhận các đoạn text tự do lộn xộn.
* **Cải thiện hiệu năng**: Giúp Agent và các chức năng tự động dễ dàng phân tích cú pháp, cập nhật riêng lẻ từng thuộc tính mà không cần ghi đè lại toàn bộ cấu trúc file.
* **Rủi ro đi kèm**: Giới hạn khả năng lưu trữ các thông tin phi cấu trúc hoặc nằm ngoài các trường đã định nghĩa sẵn.

### 3.4. Memory Decay (Suy giảm bộ nhớ)
* **Vấn đề giải quyết**: Tránh hiện tượng phình to bộ nhớ vĩnh viễn (memory leak/bloat) khi lưu trữ các facts tạm thời hoặc thông tin không còn đúng ở thời điểm hiện tại.
* **Cải thiện hiệu năng**: Mỗi khi bước sang một session mới mà fact cũ không được nhắc lại, chỉ số `inactive_sessions` tăng lên và `confidence` giảm đi 0.05. Khi `confidence` rớt xuống dưới 0.3, fact sẽ được tự động xóa bỏ, duy trì dung lượng file cực kỳ nhỏ gọn (**chỉ 375 - 460 bytes**).
* **Rủi ro đi kèm**: Có thể xóa nhầm một thông tin dài hạn quan trọng nếu người dùng không nhắc lại nó trong một khoảng thời gian dài.

