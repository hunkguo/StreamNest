// 无数据库时的演示回退数据（前端 index.php 在没有 videos 表数据时读取本文件）。
// 注意：这是占位示例，地址使用 example.com，不会真实播放。
// 部署时请改用 web/install.php 初始化数据库，或自行替换为你的真实视频清单。
const videoData = [

    {

        id: 1,

        title: "示例视频一",

        description: "示例简介：这是一段用于演示的占位视频。",

        thumbnail: "https://cdn.example.com/sample/demo1/poster.jpg",

        videoUrl: "https://cdn.example.com/sample/demo1/index.m3u8",

        type: "application/x-mpegURL"

    },

    {

        id: 2,

        title: "示例视频二",

        description: "示例简介：部署时请替换为你的真实视频数据。",

        thumbnail: "https://cdn.example.com/sample/demo2/poster.jpg",

        videoUrl: "https://cdn.example.com/sample/demo2/index.m3u8",

        type: "application/x-mpegURL"

    },

    {

        id: 3,

        title: "示例视频三",

        description: "示例简介：可在 web/js/video-data.js 与 web/install.php 中修改。",

        thumbnail: "https://cdn.example.com/sample/demo3/poster.jpg",

        videoUrl: "https://cdn.example.com/sample/demo3/index.m3u8",

        type: "application/x-mpegURL"

    }

];
