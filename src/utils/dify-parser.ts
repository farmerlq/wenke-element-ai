/**
 * Dify 响应解析器
 * 按照Dify官方API格式解析流式响应数据，确保数据格式满足BubbleList组件需求
 */

// SSE事件接口
export interface DifyStreamEvent {
  id?: string;
  event?: string;
  data?: any;
}

// 工作流事件类型
export interface WorkflowEvent {
  event: 'workflow_started' | 'node_started' | 'node_finished' | 'workflow_finished';
  workflow_run_id?: string;
  data?: {
    workflow_run_id?: string;
    node_id?: string;
    node_type?: string;
    node_name?: string;
    title?: string;
    text?: string;
    error?: string;
    status?: string;
    elapsed_time?: number;
    execution_metadata?: {
      total_tokens?: number;
      total_price?: number;
      currency?: string;
    };
    total_tokens?: number;
    total_steps?: number;
    metadata?: AnyObject;
  };
  message?: string;
}

// Dify标准消息格式接口
export interface DifyMessageData {
  id?: string;
  answer?: string;
  conversation_id?: string;
  message_id?: string;
  created_at?: number;
  metadata?: {
    usage?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
  };
}

// Dify工作流数据格式接口
export interface DifyWorkflowData {
  id?: string;
  workflow_id?: string;
  text?: string;
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
  finish_reason?: string;
  files?: any[];
}

// 用于BubbleList组件的消息项接口
export interface BubbleListItem {
  key: number;
  content: string;
  role: 'ai' | 'user' | 'system';
  avatar?: string;
  typing?: boolean;
  [key: string]: any;
}

export class DifyParser {
  private buffer = '';

  /**
   * 解析Dify流式响应
   * @param chunk 原始数据块
   * @returns 解析后的内容数组
   */
  parseChunk(chunk: string | AnyObject): string[] {
    const contents: string[] = [];

    try {
      if (typeof chunk === 'string') {
        // 防止缓冲区过大
        if (this.buffer.length > 10000) {
          console.warn('Dify解析器缓冲区过大，重置缓冲区');
          this.buffer = '';
        }

        // 尝试解码Unicode转义序列
        let decodedChunk = chunk;
        try {
          // 简单的Unicode解码，避免复杂的正则表达式
          if (decodedChunk.includes('\\u') && !decodedChunk.includes('<') && !decodedChunk.includes('>')) {
            // 使用更安全的方式解码Unicode转义序列
            decodedChunk = decodedChunk.replace(/\\u([0-9a-fA-F]{4})/g, (match, hex) => {
              try {
                return String.fromCharCode(Number.parseInt(hex, 16));
              }
              catch {
                return match; // 如果解码失败，保留原样
              }
            });
          }
        }
        catch (decodeError) {
          console.warn('Unicode解码失败，使用原始内容:', decodeError);
        }

        this.buffer += decodedChunk;
        const lines = this.buffer.split('\n');
        this.buffer = lines.pop() || '';

        for (const line of lines) {
          const content = this.parseLine(line);
          if (content) {
            contents.push(content);
          }
        }
      }
      else if (chunk && typeof chunk === 'object') {
        // 处理text_chunk事件 - 实现逐字符流式效果
        if (chunk.event === 'text_chunk' && chunk.data && chunk.data.text) {
          const content = chunk.data.text;
          if (content && this.isValidContent(content)) {
            contents.push(content);
          }
        }
        // 处理message事件 - 单独处理以支持智能体=2格式
        else if (chunk.event === 'message') {
          // 支持多种格式：chunk.answer（智能体=2的格式）、chunk.text、chunk.data.text、outputs.answer
          const text = chunk.answer || chunk.text || (chunk.data && chunk.data.text) || (chunk.outputs && chunk.outputs.answer);
          if (text && this.isValidContent(text)) {
            contents.push(text);
          }
        }
        // 处理工作流事件
        else if (['workflow_started', 'node_started', 'node_finished', 'workflow_finished'].includes(chunk.event)) {
          // 提取工作流事件信息作为内容
          const workflowContent = this.formatWorkflowEvent(chunk as WorkflowEvent);
          if (workflowContent) {
            contents.push(workflowContent);
            // 同时将事件对象作为元数据传递
            contents.push(JSON.stringify({ event: chunk.event, data: chunk.data }));
          }
        }
        // 处理其他对象格式的数据
        else {
          const content = this.extractContent(chunk);
          if (content) {
            contents.push(content);
          }
        }
      }
    }
    catch (error) {
      console.error('解析数据块时出错:', error);
      // 重置缓冲区以防止后续解析出错
      this.buffer = '';
    }

    return contents;
  }

  /**
   * 格式化工作流事件为可读文本
   * @param event 工作流事件对象
   * @returns 格式化后的文本内容
   */
  private formatWorkflowEvent(event: WorkflowEvent): string | null {
    // 为各种事件类型提供更准确的中文描述
    const baseMessages: Record<string, string> = {
      workflow_started: '工作流开始执行',
      node_started: '节点开始执行',
      node_finished: '节点执行完成',
      workflow_finished: '工作流执行完成',
    };

    let message = baseMessages[event.event] || event.event;

    // 根据不同的事件类型添加更详细的信息
    switch (event.event) {
      case 'workflow_started':
        message = `工作流开始执行 (ID: ${event.workflow_run_id || event.data?.workflow_run_id || '未知'})`;
        break;

      case 'node_started':
        if (event.data?.title && event.data?.node_type) {
          message = `正在执行: ${event.data.title} (${event.data.node_type}类型)`;
        }
        else if (event.data?.node_type) {
          message = `正在执行: ${event.data.node_type}类型节点`;
        }
        break;

      case 'node_finished':
        if (event.data?.title && event.data?.status) {
          const statusText = event.data.status === 'succeeded' ? '成功' : event.data.status;
          let execInfo = '';
          if (event.data.elapsed_time) {
            execInfo = `, 耗时: ${event.data.elapsed_time}秒`;
          }
          message = `${event.data.title} 执行${statusText}${execInfo}`;

          // 添加执行元数据信息（如token使用情况）
          if (event.data.execution_metadata?.total_tokens) {
            message += `, 消耗token: ${event.data.execution_metadata.total_tokens}`;
          }
          if (event.data.execution_metadata?.total_price) {
            message += `, 费用: ${event.data.execution_metadata.total_price}${event.data.execution_metadata.currency || ''}`;
          }
        }
        break;

      case 'workflow_finished':
        if (event.data?.status) {
          const statusText = event.data.status === 'succeeded' ? '成功完成' : `完成，状态: ${event.data.status}`;
          let statsInfo = '';
          if (event.data.elapsed_time) {
            statsInfo = `, 总耗时: ${event.data.elapsed_time}秒`;
          }
          message = `工作流${statusText}${statsInfo}`;

          // 添加工作流统计信息
          if (event.data.total_tokens) {
            message += `, 总token: ${event.data.total_tokens}`;
          }
          if (event.data.total_steps) {
            message += `, 总步骤: ${event.data.total_steps}`;
          }
        }
        break;
    }

    // 如果事件有自定义文本，优先使用自定义文本
    if (event.message) {
      message = event.message;
    }
    else if (event.data?.text) {
      message = event.data.text;
    }

    return message;
  }

  /**
   * 解析单行数据
   * @param line 单行文本
   * @returns 解析后的内容
   */
  private parseLine(line: string): string | null {
    const trimmed = line.trim();
    if (!trimmed || trimmed === 'data: [DONE]' || trimmed === '[DONE]') {
      // 将[DONE]作为正常事件处理，而不是直接返回null
      if (trimmed === 'data: [DONE]' || trimmed === '[DONE]') {
        return '[DONE]'; // 返回[DONE]作为有效内容
      }
      return null;
    }

    // 提取SSE数据部分
    let dataStr = trimmed;
    if (trimmed.indexOf('data: ') === 0) {
      dataStr = trimmed.slice(6).trim();
    }

    try {
      // 尝试解析为JSON
      const data = JSON.parse(dataStr);

      // 先使用统一的extractContent方法提取内容
      const content = this.extractContent(data);
      if (content && content.trim().length > 0) {
        return content;
      }

      // 特殊处理工作流事件
      if (['workflow_started', 'node_started', 'node_finished', 'workflow_finished'].includes(data.event)) {
        const workflowContent = this.formatWorkflowEvent(data as WorkflowEvent);
        if (workflowContent && this.isValidContent(workflowContent)) {
          return workflowContent;
        }
      }

      // 如果JSON解析成功但没有提取到内容，可能是元数据，返回null
      return null;
    }
    catch (error) {
      console.warn('解析JSON失败，跳过此数据行:', error);

      // 尝试解码Unicode转义序列
      let decodedText = dataStr;
      try {
        // 简单的Unicode解码，避免复杂的正则表达式
        if (dataStr.includes('\\u') && !dataStr.includes('<') && !dataStr.includes('>')) {
          decodedText = dataStr.replace(/\\u([0-9a-fA-F]{4})/g, (match, hex) => {
            try {
              return String.fromCharCode(Number.parseInt(hex, 16));
            }
            catch {
              return match;
            }
          });
        }
      }
      catch { }

      // 避免将无效的JSON显示为原始文本
      // 只有当内容明显不是JSON时才尝试作为内容处理
      if (!dataStr.startsWith('{') && !dataStr.startsWith('[') && this.isValidContent(decodedText)) {
        return decodedText;
      }
      return null;
    }
  }

  /**
   * 提取实际内容
   * @param data 原始数据
   * @returns 实际文本内容
   */
  public extractContent(data: AnyObject): string | null {
    // 记录传入的事件类型和基本结构
    if (data && typeof data === 'object' && data.event) {
      // 对于未成功解析的事件，记录更详细信息
      const hasKnownContentFields = data.answer || data.text || (data.data && (data.data.text || data.data.content))
        || (data.delta && data.delta.content) || (data.outputs && data.outputs.answer)
        || data.content || data.result || data.audio;
      if (!hasKnownContentFields) {
        // 调试信息已移除
      }
    }

    // 只提取真正的回复内容，忽略所有元数据字段

    // 1. 特别处理message事件中的顶层answer字段 (根据用户提供的Dify标准格式)
    if (data?.event === 'message' && data?.answer && typeof data.answer === 'string' && data.answer.trim()) {
      return data.answer;
    }

    // 2. 处理text_chunk事件中的data.text字段
    if (data?.event === 'text_chunk' && data?.data?.text && typeof data.data.text === 'string' && data.data.text.trim()) {
      const textChunk = data.data.text.trim();
      if (this.isValidContent(textChunk)) {
        return textChunk;
      }
    }

    // 3. 处理Dify标准格式的answer字段
    if (data?.answer && typeof data.answer === 'string' && data.answer.trim()) {
      return data.answer;
    }

    // 4. 处理delta.content字段 (支持与OpenAI兼容的格式)
    if (data?.delta?.content && typeof data.delta.content === 'string' && data.delta.content.trim()) {
      const deltaContent = data.delta.content.trim();
      if (this.isValidContent(deltaContent)) {
        return deltaContent;
      }
    }

    // 5. 处理outputs.answer字段
    if (data?.outputs?.answer && typeof data.outputs.answer === 'string' && data.outputs.answer.trim()) {
      return data.outputs.answer;
    }

    // 6. 处理text字段
    if (data?.text && typeof data.text === 'string' && data.text.trim()) {
      const text = data.text.trim();
      if (this.isValidContent(text)) {
        return text;
      }
    }

    // 7. 处理content字段
    if (data?.content && typeof data.content === 'string' && data.content.trim()) {
      const content = data.content.trim();
      if (this.isValidContent(content)) {
        return content;
      }
    }

    // 8. 处理嵌套数据中的text字段
    if (data?.data?.text && typeof data.data.text === 'string' && data.data.text.trim()) {
      const nestedText = data.data.text.trim();
      if (this.isValidContent(nestedText)) {
        return nestedText;
      }
    }

    // 9. 处理嵌套数据中的content字段
    if (data?.data?.content && typeof data.data.content === 'string' && data.data.content.trim()) {
      const nestedContent = data.data.content.trim();
      if (this.isValidContent(nestedContent)) {
        return nestedContent;
      }
    }

    // 10. 处理OpenAI格式的流式响应
    if (data?.choices && Array.isArray(data.choices)) {
      const delta = data.choices[0]?.delta;
      if (delta?.content && typeof delta.content === 'string' && delta.content.trim()) {
        const openAiContent = delta.content.trim();
        if (this.isValidContent(openAiContent)) {
          return openAiContent;
        }
      }
    }

    // 11. 处理可能的其他格式
    if (data?.result && typeof data.result === 'string' && data.result.trim()) {
      const result = data.result.trim();
      if (this.isValidContent(result)) {
        return result;
      }
    }

    // 12. 处理tts_message中的audio字段（将其作为特殊内容处理）
    if (data?.event === 'tts_message' && data?.audio && typeof data.audio === 'string' && data.audio.trim()) {
      return data.audio;
    }

    // 默认情况：如果所有路径都未匹配，记录完整数据结构用于调试
    if (data && typeof data === 'object') {
      // 对于没有已知事件类型但包含数据的对象，记录其结构
      if (!data.event && Object.keys(data).length > 0) {
        // 调试信息已移除
      }
    }

    // 13. 处理纯文本响应
    if (typeof data === 'string') {
      const text = String(data).trim();
      if (text.length > 0 && this.isValidContent(text)) {
        return text;
      }
    }

    // 对于其他情况，返回null表示这不是有效内容
    return null;
  }

  /**
   * 判断内容是否为有效内容（非元数据）
   * @param content 内容字符串
   * @returns 是否为有效内容
   */
  public isValidContent(content: string): boolean {
    // 最基本的过滤：只排除空字符串和明显的控制信息
    if (!content || content.trim() === '') {
      return false;
    }

    // 排除特殊的控制信息标记，但允许[DONE]作为有效事件数据
    const controlMarkers = ['[DONE]', '[DONE', 'DONE]', 'DONE'];
    for (const marker of controlMarkers) {
      if (content === marker) {
        // 如果是精确的[DONE]字符串，作为有效事件处理
        return true;
      }
      if (content.includes(marker) && content !== marker) {
        // 如果包含在内容中但不是精确匹配，视为控制信息
        return false;
      }
    }

    // 对于所有其他情况，只要内容不为空，就视为有效
    return true;
  }

  /**
   * 验证JSON字符串是否有效
   * @param jsonString JSON字符串
   * @returns 是否为有效的JSON
   */
  public isValidJson(jsonString: string): boolean {
    try {
      JSON.parse(jsonString);
      return true;
    }
    catch {
      return false;
    }
  }

  /**
   * 清理JSON字符串，修复常见的格式问题
   * @param jsonString 原始JSON字符串
   * @returns 清理后的JSON字符串
   */
  public cleanJsonString(jsonString: string): string {
    let cleaned = jsonString;

    // 移除可能导致解析错误的控制字符
    cleaned = cleaned
      .replace(/[\u0000-\u001F\u007F-\u009F]/g, '') // 移除控制字符
      .replace(/\n/g, '\\n') // 转义换行符
      .replace(/\r/g, '\\r') // 转义回车符
      .replace(/\t/g, '\\t'); // 转义制表符

    // 尝试修复不完整的JSON（根据用户错误信息中的截断问题）
    // 检查是否以不完整的字符串结尾（用户错误信息显示message_id字段被截断）
    if (cleaned.includes('"') && !cleaned.match(/"[^"]*$/)) {
      // 如果以不完整的字符串结尾，尝试补全引号
      const lastQuoteIndex = cleaned.lastIndexOf('"');
      if (lastQuoteIndex > -1 && lastQuoteIndex === cleaned.length - 1) {
        // 如果以引号结尾，可能是完整的字符串
      }
      else {
        // 尝试找到最后一个不完整的字符串并补全
        cleaned = cleaned.replace(/"[^"]*$/, (match) => {
          // 如果匹配到类似 "message_id": "0e7a1b9e-3c96-429d-b6e1-d4 这样的不完整字符串
          if (match.includes(':')) {
            const parts = match.split(':');
            if (parts.length >= 2) {
              const key = parts[0].trim();
              const value = parts.slice(1).join(':').trim();
              if (value.startsWith('"') && !value.endsWith('"')) {
                // 补全字符串引号
                return `${key}:${value}"`;
              }
            }
          }
          return match;
        });
      }
    }

    // 智能补全不完整的JSON字符串
    if (cleaned.includes('"message_id":') && !cleaned.endsWith('"') && !cleaned.endsWith('}')) {
      // 查找最后一个引号的位置
      const lastQuoteIndex = cleaned.lastIndexOf('"');
      if (lastQuoteIndex > -1 && lastQuoteIndex > cleaned.length - 10) {
        // 使用正则表达式匹配类似 "message_id": "0e7a1b9e-3c96-429d-b6e1-d4 这样的模式
        cleaned = cleaned.replace(/("message_id"\s*:\s*"[^"]*)$/, (match) => {
          // 如果匹配到的字符串看起来像UUID的一部分，补全引号和括号
          if (match.length > 20 && /[0-9a-f-]+$/i.test(match)) {
            return `${match}"`;
          }
          return match;
        });
      }
    }

    // 专门处理用户错误日志中出现的截断格式
    if (cleaned.includes('"message_id":') && cleaned.includes('"event":') && !cleaned.endsWith('}')) {
      // 检查是否缺少闭合括号
      const openBraces = (cleaned.match(/\{/g) || []).length;
      const closeBraces = (cleaned.match(/\}/g) || []).length;
      if (openBraces > closeBraces) {
        cleaned += '}'.repeat(openBraces - closeBraces);
      }

      // 专门处理用户错误日志中的UUID截断模式
      const truncatedUUIDMatch = cleaned.match(/"message_id"\s*:\s*"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{1,12})"[^"]*/);
      if (truncatedUUIDMatch && truncatedUUIDMatch[1]) {
        const truncatedUUID = truncatedUUIDMatch[1];
        // 如果UUID被截断（少于36个字符），使用随机字符补全
        if (truncatedUUID.length < 36) {
          const fullUUID = truncatedUUID.padEnd(36, '0').substring(0, 36);
          cleaned = cleaned.replace(`"message_id": "${truncatedUUID}`, `"message_id": "${fullUUID}"`);
        }
      }
    }

    // 检查是否以不完整的对象结尾
    if (cleaned.includes('{') && !cleaned.includes('}')) {
      // 如果以不完整的对象结尾，尝试补全括号
      // 先检查是否包含常见的字段，如果是则尝试补全
      if (cleaned.includes('"event"') || cleaned.includes('"message_id"') || cleaned.includes('"data"')) {
        cleaned += '}';
      }
    }

    // 检查是否以不完整的数组结尾
    if (cleaned.includes('[') && !cleaned.includes(']')) {
      // 如果以不完整的数组结尾，尝试补全括号
      cleaned += ']';
    }

    return cleaned;
  }

  /**
   * 清理和重置
   */
  reset(): void {
    this.buffer = '';
  }
}

/**
 * Dify响应渲染器
 * 负责将解析后的内容渲染到UI，确保数据格式满足BubbleList组件需求
 */
export class DifyRenderer {
  private parser = new DifyParser();
  private accumulatedContent = '';
  private bufferTimer: any = null;

  private isComplete = false;

  /**
   * 处理新的数据块
   * @param chunk 原始数据块
   * @param onContent 内容回调函数（支持元数据）
   * @param onComplete 完成回调函数
   * @param onError 错误处理回调函数
   */
  handleChunk(
    chunk: string | AnyObject,
    onContent: (content: string, metadata?: AnyObject) => void,
    onComplete?: () => void,
    onError?: (error: Error) => void,
  ): void {
    try {
      // 记录传入的chunk信息
      if (typeof chunk === 'string') {
        // 调试信息已移除
      }
      else if (chunk && typeof chunk === 'object') {
        if (chunk.event) {
          // 对于未被成功处理的事件类型，记录更详细信息
          const commonEvents = ['text_chunk', 'message', 'workflow_started', 'node_started', 'node_finished', 'workflow_finished', 'message_end', 'tts_message', 'tts_message_end'];
          if (!commonEvents.includes(chunk.event)) {
            // 调试信息已移除
          }
        }
      }

      // 处理字符串格式的数据
      if (typeof chunk === 'string') {
        const trimmed = chunk.trim();
        if (trimmed) {
          // 解码Unicode转义序列
          let decodedChunk = trimmed;
          try {
            // 检查是否包含Unicode转义序列，且不是HTML标签
            if (trimmed.includes('\\u') && !trimmed.includes('<') && !trimmed.includes('>')) {
              // 构建安全的JSON字符串进行解码
              // 只替换必要的字符，避免破坏有效内容
              let safeStr = trimmed.replace(/\\"/g, '\\\\"'); // 转义已有的转义引号
              safeStr = safeStr.replace(/\\\\u/g, '\\u'); // 确保Unicode转义序列格式正确
              // 只在内容看起来像文本时尝试解码
              if (/^(?:[\u0000-\u007F]|\\\\u[0-9a-fA-F]{4})*$/.test(safeStr)) {
                decodedChunk = JSON.parse(`"${safeStr}"`);
              }
            }
          }
          catch { }

          // 检查是否为SSE格式的数据
          if (decodedChunk.startsWith('data: ')) {
            const jsonStr = decodedChunk.substring(6).trim();
            if (jsonStr === '[DONE]') {
              // 将[DONE]作为正常事件处理，而不是JSON解析错误
              const doneEvent = {
                event: 'done',
                data: '[DONE]',
                type: 'completion',
              };
              this.handleChunk(doneEvent, onContent, onComplete);
              return;
            }
            try {
              // 尝试解析JSON，处理可能的格式问题
              try {
                const parsed = JSON.parse(jsonStr);
                processParsedObject.call(this, parsed, onContent, onComplete);
              }
              catch {
                // 如果是明显的JSON格式错误，尝试清理和修复
                if (jsonStr.includes('}{')) {
                  // 处理多个JSON对象拼接的情况
                  const jsonObjects = jsonStr.split('}{').map((part, index, arr) => {
                    if (index === 0)
                      return `${part}}`; // 第一个对象补全右括号
                    if (index === arr.length - 1)
                      return `{${part}`; // 最后一个对象补全左括号
                    return `{${part}}`; // 中间对象补全括号
                  });

                  for (const objStr of jsonObjects) {
                    try {
                      const obj = JSON.parse(objStr);
                      processParsedObject.call(this, obj, onContent, onComplete);
                    }
                    catch {
              
                    }
                  }
                  return;
                }

                // 预验证JSON格式
                const trimmedJson = jsonStr.trim();
                if (!trimmedJson.startsWith('{') && !trimmedJson.startsWith('[')) {
                  console.warn('非JSON格式数据:', {
                    content: trimmedJson,
                    length: trimmedJson.length,
                    startsWith: trimmedJson.substring(0, 20),
                  });
                  // 对于非JSON格式的内容，如果是有效文本则直接显示
                  if (this.parser.isValidContent(trimmedJson)) {
                    const textEvent = {
                      event: 'text_chunk',
                      data: trimmedJson,
                      type: 'text',
                    };
                    this.handleChunk(textEvent, onContent, onComplete);
                  }
                  return;
                }

                // 先尝试直接解析
                if (!this.parser.isValidJson(jsonStr)) {
                  // 清理后重试
                  const cleanedJson = this.parser.cleanJsonString(jsonStr);
                  if (!this.parser.isValidJson(cleanedJson)) {
                    // 专门处理用户错误日志中出现的截断格式
                    if (jsonStr.includes('"message_id":') && jsonStr.includes('"event":')
                      && jsonStr.includes('"message"') && !jsonStr.endsWith('}')) {
                      // 尝试智能补全截断的JSON
                      let fixedJson = jsonStr;
                      // 补全缺失的引号
                      if (fixedJson.includes('"message_id":') && !fixedJson.includes('"message_id":"')) {
                        fixedJson = fixedJson.replace(/"message_id"\s*:\s*([^,"\s]+)(,|\})/g, '"message_id":"$1"$2');
                      }

                      // 专门处理截断的UUID格式（如：0e7a1b9e-3c96-429d-b6e1-d4）
                      const messageIdMatch = fixedJson.match(/"message_id"\s*:\s*"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{1,12})"?(,|\})?/);
                      if (messageIdMatch && messageIdMatch[1]) {
                        const uuidPart = messageIdMatch[1];
                        // 如果UUID看起来不完整（少于36个字符且没有完整的UUID格式）
                        if (uuidPart.length < 36 && !uuidPart.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/)) {
                          // 生成一个完整的UUID来替换截断的部分
                          const fullUUID = uuidPart.padEnd(36, '0').substring(0, 36);
                          fixedJson = fixedJson.replace(`"message_id":"${uuidPart}"`, `"message_id":"${fullUUID}"`);
                        }
                      }

                      // 补全闭合括号
                      const openBraces = (fixedJson.match(/\{/g) || []).length;
                      const closeBraces = (fixedJson.match(/\}/g) || []).length;
                      if (openBraces > closeBraces) {
                        fixedJson += '}'.repeat(openBraces - closeBraces);
                      }

                      // 再次尝试解析修复后的JSON
                      if (this.parser.isValidJson(fixedJson)) {
                        try {
                          const parsed = JSON.parse(fixedJson);
                          processParsedObject.call(this, parsed, onContent, onComplete);
                          return;
                        }
                        catch {
                  
                        }
                      }

                      // 如果修复失败，尝试提取有效内容部分
                      if (fixedJson.includes('"event": "message"') && fixedJson.includes('"data":')) {
                        // 尝试提取data字段的内容
                        const dataMatch = fixedJson.match(/"data"\s*:\s*\{([^}]*)\}/);
                        if (dataMatch && dataMatch[1]) {
                          const textMatch = dataMatch[1].match(/"text"\s*:\s*"([^"]*)"/);
                          if (textMatch && textMatch[1]) {
                            const text = textMatch[1];
                            if (text && this.parser.isValidContent(text)) {
                              this.accumulatedContent += text;
                              onContent(text);
                              return;
                            }
                          }
                        }
                      }

                      // 最后尝试：如果包含有效的文本内容但JSON格式损坏，直接提取文本
                      const textContentMatch = jsonStr.match(/"text"\s*:\s*"([^"]+)"/);
                      if (textContentMatch && textContentMatch[1]) {
                        const text = textContentMatch[1];
                        if (text && this.parser.isValidContent(text)) {
                          this.accumulatedContent += text;
                          onContent(text);
                          return;
                        }
                      }
                    }

                    console.warn('JSON格式验证失败:', {
                      originalLength: jsonStr.length,
                      cleanedLength: cleanedJson.length,
                      sample: jsonStr.substring(0, 150),
                      error: 'Invalid JSON format',
                    });
                    return;
                  }
                  else {
                    // 清理后的JSON有效，继续解析
                    try {
                      const parsed = JSON.parse(cleanedJson);
                      processParsedObject.call(this, parsed, onContent, onComplete);
                      return;
                    }
                    catch {
              
                    }
                  }
                }
                // 对于非JSON格式的内容，如果是有效文本则直接显示
                if (!jsonStr.startsWith('{') && !jsonStr.startsWith('[') && this.parser.isValidContent(jsonStr)) {
                  this.accumulatedContent += jsonStr;
                  onContent(jsonStr);
                }
                return;
              }
            }
            catch {
      
            }
          }

          function processParsedObject(this: any, parsed: any, onContent: (content: string, metadata?: any) => void, onComplete?: () => void) {
          // 优先检查是否为text_chunk事件
            if (parsed.event === 'text_chunk' && parsed.data && parsed.data.text) {
              const text = parsed.data.text;
              if (text && this.parser.isValidContent(text)) {
                this.accumulatedContent += text;
                onContent(text);
                return;
              }
            }
            // 对于message事件，单独处理，优先检查根级answer字段
            else if (parsed.event === 'message') {
            // 支持多种格式：parsed.answer（智能体=2的格式）、parsed.text、parsed.data.text、outputs.answer、delta.content
              const text = parsed.answer || parsed.text || (parsed.data && parsed.data.text) || (parsed.outputs && parsed.outputs.answer) || (parsed.delta && parsed.delta.content);
              if (text && this.parser.isValidContent(text)) {
                this.accumulatedContent += text;
                onContent(text);
                return;
              }
            }
            // 处理工作流事件
            if (['workflow_started', 'node_started', 'node_finished', 'workflow_finished'].includes(parsed.event)) {
            // 直接将工作流事件对象传递给onContent回调
              onContent('', parsed);
              return;
            }
            // 处理其他格式
            this.handleChunk(parsed, onContent, onComplete);
          }
        }
        else {
        // 简化的JSON解析
          try {
            const parsed = JSON.parse(chunk);
            processSingleObject.call(this, parsed, onContent, onComplete);
          }
          catch {
          // 简单的错误处理：只处理分割的JSON对象
            if (chunk.includes('}{')) {
              const parts = chunk.split('}{');
              for (let i = 0; i < parts.length; i++) {
                let part = parts[i];
                if (i === 0)
                  part += '}';
                else if (i === parts.length - 1)
                  part = `{${part}`;
                else part = `{${part}}`;

                try {
                  const obj = JSON.parse(part.trim());
                  processSingleObject.call(this, obj, onContent, onComplete);
                }
                catch {
                // 跳过无效的片段
                }
              }
            }
            else {
            // 对于非JSON内容，如果是有效文本则直接显示
              const textContent = chunk.trim();
              if (textContent && !textContent.startsWith('{') && !textContent.startsWith('[') && this.parser.isValidContent(textContent)) {
                this.accumulatedContent += textContent;
                onContent(textContent);
              }
            }
          }
        }

        function processSingleObject(this: any, parsed: any, onContent: (content: string, metadata?: any) => void, onComplete?: () => void) {
        // 处理字符流事件（text_chunk和message本质一样，都是字符流叠加事件）
          if (parsed.event === 'text_chunk' || parsed.event === 'message') {
          // 支持多种格式：parsed.answer（智能体=2的格式）优先，然后是其他字段
            const text = parsed.answer || parsed.text || (parsed.data && parsed.data.text) || (parsed.outputs && parsed.outputs.answer) || (parsed.delta && parsed.delta.content);
            // 对于字符流事件，只要内容不为空就传递，不过于严格过滤
            if (text && typeof text === 'string' && text.trim().length > 0) {
              this.accumulatedContent += text;
              onContent(text);
              return;
            }
          }
          // 处理事件属性和文本内容在同一个对象中的情况（根据测试脚本需求）
          else if ('event' in parsed && 'text' in parsed) {
          // 这是测试脚本期望的格式：text字段直接在事件对象中
            const text = parsed.text;
            if (text && typeof text === 'string' && text.trim().length > 0) {
              this.accumulatedContent += text;
              onContent(text);
              return;
            }
          }
          this.handleChunk(parsed, onContent, onComplete);
        }
      }

      // 处理对象格式的数据
      if (chunk && typeof chunk === 'object') {
      // 添加调试日志，记录接收到的所有事件类型和关键字段
        if (chunk.event) {
  
          // 对于message事件，记录更多详细信息
          if (chunk.event === 'message') {
    
          }
        }
        let content = null;

        // 1. 处理字符流事件（text_chunk和message都是字符流叠加事件）
        if (chunk.event === 'text_chunk') {
          const text = chunk.data?.text || chunk.text || chunk.content;
          if (text && typeof text === 'string' && text.trim().length > 0) {
            content = text;
          }
        }
        // 特别处理message事件，根据用户提供的示例，message事件直接在顶层包含answer字段
        else if (chunk.event === 'message') {
        // 直接使用顶层answer字段，这是用户提供的Dify标准格式
          const text = chunk.answer || chunk.text || (chunk.data && chunk.data.text) || (chunk.outputs && chunk.outputs.answer) || (chunk.delta && chunk.delta.content);
          if (text && typeof text === 'string' && text.trim().length > 0) {
            content = text;
          }
        }
        // 处理tts_message事件
        else if (chunk.event === 'tts_message') {
        // 将tts_message作为元数据传递
          if (onContent) {
            onContent('', chunk);
          }
          return;
        }
        // 处理tts_message_end事件
        else if (chunk.event === 'tts_message_end') {
        // 将tts_message_end作为元数据传递
          if (onContent) {
            onContent('', chunk);
          }
          return;
        }
        // 处理事件属性和文本内容在同一个对象中的情况（根据测试脚本需求）
        else if ('event' in chunk && 'text' in chunk) {
        // 这是测试脚本期望的格式：text字段直接在事件对象中
          const text = chunk.text;
          if (text && typeof text === 'string' && text.trim().length > 0) {
            content = text;
          }
        }
        // 特别处理message_end事件，将其作为元数据传递
        else if (chunk.event === 'message_end') {
        // 传递message_end事件作为元数据
          if (onContent) {
            onContent('', chunk);
          }
          return;
        }
        // 2. 处理Dify格式的text字段
        else if (chunk.text && typeof chunk.text === 'string') {
          content = this.parser.extractContent({ text: chunk.text });
        }
        // 3. 处理Dify格式的answer字段
        else if (chunk.answer && typeof chunk.answer === 'string') {
          content = this.parser.extractContent({ answer: chunk.answer });
        }
        // 4. 处理delta格式（OpenAI兼容）
        else if (chunk.choices && Array.isArray(chunk.choices)) {
          const delta = chunk.choices[0]?.delta;
          if (delta?.content) {
            content = this.parser.extractContent({ content: delta.content });
          }
        }
        // 5. 处理流式响应中的content字段
        else if (chunk.content && typeof chunk.content === 'string') {
          content = this.parser.extractContent({ content: chunk.content });
        }
        // 6. 处理嵌套数据结构
        else if (chunk.data && typeof chunk.data === 'object') {
          content = this.parser.extractContent(chunk.data);
        }
        // 7. 使用parser统一提取内容
        else {
          content = this.parser.extractContent(chunk);
        }

        if (content) {
          this.accumulatedContent += content;
          // 立即发送内容，提供实时的流式效果
          onContent(content);
        }
      }

      // 处理完成信号的多种情况
      const isComplete = typeof chunk === 'string'
        ? (chunk as string) === '[DONE]'
        : chunk?.finish_reason === 'stop'
          || chunk?.event === 'done'
          || chunk?.event === 'message_end'
          || chunk?.event === 'tts_message_end'
          || chunk?.event === 'workflow_finished'
          || chunk?.status === 'completed';

      if (onComplete && isComplete && !this.isComplete) {
        this.isComplete = true;
        onComplete();
      }
    }
    catch (error) {
      console.error('Dify解析器处理数据块时出错:', error);
      // 使用错误回调函数通知错误
      if (onError && error instanceof Error) {
        onError(error);
      }
      else {
        // 尝试返回错误信息，确保UI能显示错误状态
        try {
          onContent(`处理响应时出错: ${error instanceof Error ? error.message : '未知错误'}`);
        }
        catch { }
      }
    }
    finally {
      // 移除return语句，确保后续代码能够执行
    }
  }

  /**
   * 获取完整内容
   * @returns 完整响应内容
   */
  getFullContent(): string {
    return this.accumulatedContent;
  }

  /**
   * 重置状态
   */
  reset(): void {
    this.parser.reset();
    this.accumulatedContent = '';
    if (this.bufferTimer) {
      clearTimeout(this.bufferTimer);
      this.bufferTimer = null;
    }
    this.isComplete = false;
  }

  /**
   * 通知流已结束
   * @param onComplete 完成回调函数
   */
  notifyEnd(onComplete?: () => void): void {
    if (!this.isComplete && onComplete) {
      this.isComplete = true;
      onComplete();
    }
  }

  /**
   * 处理SSE数据行，直接转换为BubbleListItem格式
   * @param sseLine SSE数据行
   * @param messageKey 消息唯一标识
   * @param avatar 头像URL
   * @returns 转换后的BubbleListItem
   */
  parseToBubbleListItem(
    sseLine: string,
    messageKey: number,
    avatar?: string,
  ): BubbleListItem | null {
    try {
      // 提取SSE数据
      let data = sseLine;
      if (sseLine.startsWith('data: ')) {
        data = sseLine.substring(6).trim();
      }

      // 如果是结束标记，将其作为正常的事件处理
      if (data === '[DONE]') {
        // 将[DONE]作为正常事件处理，提供有意义的内容
        const doneEvent = {
          event: 'done',
          type: 'completion',
          status: 'completed',
          data: '[DONE]',
        };
        return {
          key: messageKey,
          content: '[完成]', // 提供用户友好的完成提示
          role: 'system',
          metadata: doneEvent,
          avatar: avatar || '/avatar-assistant.png',
        };
      }

      // 尝试解析JSON
      let parsedData: any;
      try {
        parsedData = JSON.parse(data);
      }
      catch {
        // 如果不是有效的JSON，直接作为内容处理
        parsedData = { content: data };
      }

      // 提取内容
      const content = this.parser.extractContent(parsedData);

      if (content) {
        return {
          key: messageKey,
          content,
          role: 'ai', // 默认AI角色
          avatar: avatar || '/avatar-assistant.png',
          typing: false,
        };
      }

      return null;
    }
    catch (error) {
      console.error('转换为BubbleListItem时出错:', error);
      return null;
    }
  }

  /**
   * 批量处理SSE数据行并转换为BubbleListItem数组
   * @param sseData SSE数据块
   * @param startingKey 起始消息键
   * @param avatar 头像URL
   * @returns BubbleListItem数组
   */
  batchParseToBubbleListItems(
    sseData: string,
    startingKey: number = 0,
    avatar?: string,
  ): BubbleListItem[] {
    const items: BubbleListItem[] = [];

    try {
      // 按行分割数据
      const lines = sseData.split('\n');

      // 为每行数据创建一个BubbleListItem
      for (const line of lines) {
        if (line.trim()) {
          const item = this.parseToBubbleListItem(line, startingKey + items.length, avatar);
          if (item) {
            items.push(item);
          }
        }
      }
    }
    catch (error) {
      console.error('批量转换为BubbleListItem时出错:', error);
    }

    return items;
  }
}

// 使用示例
export function useDifyParser() {
  const renderer = new DifyRenderer();

  return {
    renderer,
    parseChunk: renderer.handleChunk.bind(renderer),
    getFullContent: renderer.getFullContent.bind(renderer),
    reset: renderer.reset.bind(renderer),
    notifyEnd: renderer.notifyEnd.bind(renderer),
  };
}

// 类型定义
export interface AnyObject {
  [key: string]: any;
}
