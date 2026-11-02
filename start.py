#!/usr/bin/env python3
"""Original Chinese exercise, using the official Ollama CLI and chat API."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
VERSION = '0.40.13'
MODEL = 'qwen3:0.6b'
MODEL_DIGEST = '7df6b6e09427a769808717c0a93cadc4ae99ed4eb8bf5ca557c90846becea435'
PORT = 11439
API = 'http://127.0.0.1:' + str(PORT)
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def call(path, data=None, timeout=100):
    req = urllib.request.Request(API + path, data=json.dumps(data).encode() if data is not None else None, headers={'Content-Type': 'application/json'})
    with HTTP.open(req, timeout=timeout) as response:
        return json.load(response)

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def runtime():
    target = ROOT / '.runtime'
    bundle = target / 'bundle'
    arch = platform.machine().lower()
    if sys.platform == 'darwin':
        name, sha = 'ollama-darwin.tgz', 'bae29252232b9e1358cf5801a7d65a07442af18fb5467cb68c7fc3711f59c511'
    elif sys.platform == 'win32' and arch in {'arm64', 'aarch64'}:
        name, sha = 'ollama-windows-arm64.zip', '32324e770eef0416abb77e42a31a9d79bd752bd9c28582e422666ba24550d56c'
    else:
        raise RuntimeError('本入口只自动准备macOS或Windows ARM64官方包。Linux/Windows x64请按RUN.md安装官方CLI，再传 --ollama-bin；这些系统本期未实测。')
    binary = bundle / ('ollama.exe' if sys.platform == 'win32' else 'ollama')
    if binary.is_file():
        return binary
    target.mkdir(exist_ok=True)
    archive = target / name
    if not archive.exists():
        curl = shutil.which('curl') or shutil.which('curl.exe')
        if not curl:
            raise RuntimeError('缺少curl。请安装官方CLI并传 --ollama-bin。')
        print('首次下载官方Ollama固定版本；软件约187MB，模型另约523MB。', flush=True)
        subprocess.run([curl, '-fL', '--connect-timeout', '10', '--max-time', '240', '--retry', '0', 'https://github.com/ollama/ollama/releases/download/v' + VERSION + '/' + name, '-o', str(archive)], check=True, timeout=250)
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != sha:
        raise RuntimeError('官方软件包校验未通过；保留文件供排查，不继续执行。')
    bundle.mkdir(exist_ok=True)
    if name.endswith('.zip'):
        with zipfile.ZipFile(archive) as z:
            for n in z.namelist():
                if n.startswith('/') or '..' in Path(n).parts:
                    raise RuntimeError('归档路径异常')
            z.extractall(bundle)
    else:
        with tarfile.open(archive) as t:
            for m in t.getmembers():
                if m.name.startswith('/') or '..' in Path(m.name).parts or (m.issym() and (m.linkname.startswith('/') or '..' in Path(m.linkname).parts)):
                    raise RuntimeError('归档路径异常')
            t.extractall(bundle)
    if not binary.is_file():
        raise RuntimeError('未在官方包中找到CLI')
    return binary

def main():
    p = argparse.ArgumentParser(description='用本地小模型做中文摘要和公告字段提取；不连接云端模型')
    p.add_argument('--ollama-bin', type=Path, help='已有官方CLI的完整路径')
    p.add_argument('--model-dir', type=Path, help='已有模型目录；只在独占使用且明确权属时指定')
    p.add_argument('--task', choices=['all', 'summary', 'extract'], default='all')
    args = p.parse_args()
    if sys.version_info < (3, 9):
        raise RuntimeError('需要Python3.9或更新版本')
    binary = (args.ollama_bin or runtime()).resolve()
    if not binary.is_file():
        raise RuntimeError('CLI路径不存在')
    try:
        with socket.create_connection(('127.0.0.1', PORT), timeout=1):
            raise RuntimeError('11439已占用。为避免干扰已有服务，本入口停止；不要结束不属于自己的进程。')
    except ConnectionRefusedError:
        pass
    models = (args.model_dir or ROOT / '.runtime/models').resolve()
    models.mkdir(parents=True, exist_ok=True)
    output = ROOT / 'output'
    output.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update(OLLAMA_HOST='127.0.0.1:' + str(PORT), OLLAMA_MODELS=str(models), OLLAMA_NO_CLOUD='1', OLLAMA_NUM_PARALLEL='1', OLLAMA_MAX_LOADED_MODELS='1', OLLAMA_CONTEXT_LENGTH='2048', OLLAMA_NOHISTORY='1', OLLAMA_KEEP_ALIVE='0')
    with (output / 'service.log').open('w', encoding='utf-8') as log:
        proc = subprocess.Popen([str(binary), 'serve'], env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(30):
                if proc.poll() is not None:
                    raise RuntimeError('服务提前退出，请查看output/service.log；日志不宜直接公开。')
                try:
                    version = call('/api/version', timeout=1)
                    break
                except (OSError, ValueError):
                    time.sleep(.5)
            else:
                raise RuntimeError('15秒内服务未就绪')
            if version.get('version') != VERSION:
                raise RuntimeError('CLI版本与本练习固定版本不一致')
            tags = call('/api/tags')['models']
            found = next((m for m in tags if m['name'] == MODEL), None)
            if found is None:
                print('下载真实模型 qwen3:0.6b，约523MB，最长等待240秒。', flush=True)
                result = call('/api/pull', {'model': MODEL, 'stream': False}, timeout=240)
                if result.get('status') != 'success':
                    raise RuntimeError('模型下载未成功：' + str(result))
                found = next((m for m in call('/api/tags')['models'] if m['name'] == MODEL), None)
            if not found or found.get('digest') != MODEL_DIGEST:
                raise RuntimeError('模型标签内容已变化，与本期固定清单不同，请先人工核验后更新练习。')
            fixtures = json.loads((ROOT / 'fixtures.json').read_text(encoding='utf-8'))
            records = []
            for fixture in fixtures:
                if args.task != 'all' and fixture['task'] != args.task:
                    continue
                payload = json.loads((ROOT / 'requests' / (fixture['id'] + '.json')).read_text(encoding='utf-8'))
                payload['messages'][1]['content'] = fixture['text']
                response = call('/api/chat', payload)
                save(output / (fixture['id'] + '-response.json'), response)
                content = response['message']['content']
                (output / (fixture['id'] + '.txt')).write_text(content + '\n', encoding='utf-8')
                exact = json.loads(content) == fixture['expected'] if fixture['task'] == 'extract' else None
                records.append({'id': fixture['id'], 'exact_expected': exact, 'manual_review_required': fixture['task'] == 'summary', 'content': content})
                print('\n' + fixture['id'] + '\n' + content, flush=True)
            ps = call('/api/ps')
            call('/api/generate', {'model': MODEL, 'keep_alive': 0})
            save(output / 'verification.json', {'version': version, 'model': found, 'loaded': ps, 'after_unload': call('/api/ps'), 'results': records, 'scope': '结构化字段按原创样例核对；摘要必须人工逐条核原文，不将HTTP成功当作语义正确。'})
            if any(r['exact_expected'] is False for r in records):
                raise RuntimeError('结构化结果与本期样例预期不符。原始输出已保留，不能直接用于正式活动。')
            print('\n完成：查看output/中的摘要、JSON与verification.json。摘要仍需人工核对。', flush=True)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
            print('本入口启动的Ollama服务已停止。', flush=True)

if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print('未完成：' + str(exc), file=sys.stderr)
        sys.exit(1)
