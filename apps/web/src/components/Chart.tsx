"use client";
import { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import {
  LineChart,
  BarChart,
  PieChart,
  HeatmapChart,
  ScatterChart,
} from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  AriaComponent,
  VisualMapComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { ChartSpec, numeric, Row } from "@/lib/api";
echarts.use([
  LineChart,
  BarChart,
  PieChart,
  HeatmapChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  AriaComponent,
  VisualMapComponent,
  CanvasRenderer,
]);
export default function Chart({
  spec,
  theme,
  onSelect,
}: {
  spec: ChartSpec;
  theme: string;
  onSelect?: (value: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || !spec.rows.length) return;
    const chart = echarts.init(ref.current);
    const dark = theme === "dark";
    const ink = dark ? "#A7B5C2" : "#65727F";
    const border = dark ? "#344250" : "#E7EBEE";
    const keys = Object.keys(spec.rows[0]).filter(
      (k) =>
        k !== "name" &&
        spec.rows.some(
          (r) =>
            r[k] !== null &&
            r[k] !== undefined &&
            Number.isFinite(Number(r[k])),
        ),
    );
    const option: echarts.EChartsCoreOption = {
      color: ["#2F6FED", "#13A88A", "#E3A14B", "#8495AE", "#785E9B"],
      animationDuration: matchMedia("(prefers-reduced-motion: reduce)").matches
        ? 0
        : 250,
      aria: { enabled: true },
      textStyle: { fontFamily: "Geist, sans-serif", color: ink },
      tooltip: {
        trigger: spec.kind === "donut" ? "item" : "axis",
        valueFormatter: (v: unknown) => numeric(v) + " " + spec.unit,
      },
      legend: {
        bottom: 0,
        textStyle: { color: ink, fontSize: 10 },
        icon: "circle",
        itemWidth: 7,
        itemHeight: 7,
      },
      grid: { left: 58, right: 20, top: 20, bottom: 55 },
      xAxis: {
        type: "category",
        data: spec.rows.map((r) => r.name),
        axisLabel: { color: ink, fontSize: 10, hideOverlap: true },
        axisLine: { lineStyle: { color: border } },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        axisLabel: {
          color: ink,
          fontSize: 10,
          formatter: (v: number) =>
            Math.abs(v) >= 1e6
              ? (v / 1e6).toFixed(1) + "m"
              : Math.abs(v) >= 1000
                ? (v / 1000).toFixed(0) + "k"
                : String(v),
        },
        splitLine: { lineStyle: { color: border, type: "dashed" } },
      },
      series: keys.map((key, i) => ({
        name: key === "value" ? spec.unit : key.replaceAll("_", " "),
        type: spec.kind === "line" ? "line" : "bar",
        showSymbol: false,
        smooth: false,
        connectNulls: false,
        barMaxWidth: 26,
        lineStyle: {
          width: i === 0 ? 2.5 : 1.5,
          type: key === "target" ? "dashed" : "solid",
        },
        areaStyle:
          spec.kind === "line" && i === 0 ? { opacity: 0.055 } : undefined,
        data: spec.rows.map((r) => (r[key] === null ? null : Number(r[key]))),
      })),
    };
    if (spec.kind === "donut") {
      delete option.xAxis;
      delete option.yAxis;
      option.series = [
        {
          name: spec.unit,
          type: "pie",
          radius: ["55%", "77%"],
          center: ["50%", "44%"],
          label: { show: false },
          itemStyle: { borderColor: dark ? "#18232E" : "#fff", borderWidth: 3 },
          data: spec.rows.map((r) => ({
            name: String(r.name),
            value: Number(r.value),
          })),
        },
      ];
    }
    if (spec.kind === "heatmap") {
      const cohorts = [...new Set(spec.rows.map((r) => String(r.name)))];
      const periods = [...new Set(spec.rows.map((r) => Number(r.period)))].sort(
        (a, b) => a - b,
      );
      option.grid = { left: 65, right: 15, top: 15, bottom: 65 };
      option.legend = { show: false };
      option.xAxis = {
        type: "category",
        data: periods.map((p) => "M" + p),
        axisLabel: { fontSize: 9, color: ink },
        axisLine: { show: false },
        axisTick: { show: false },
      };
      option.yAxis = {
        type: "category",
        inverse: true,
        data: cohorts,
        axisLabel: { fontSize: 9, color: ink },
        axisLine: { show: false },
        axisTick: { show: false },
      };
      option.visualMap = {
        min: 0,
        max: 100,
        orient: "horizontal",
        left: "center",
        bottom: 0,
        itemWidth: 10,
        itemHeight: 120,
        text: ["100%", "0%"],
        textStyle: { color: ink, fontSize: 9 },
        inRange: { color: ["#edf3f1", "#a1d2bf", "#13a88a", "#075f4f"] },
      };
      option.tooltip = {
        trigger: "item",
        formatter: (input: unknown) => {
          const p = input as { value: number[] };
          return `${cohorts[p.value[1]]} / month ${periods[p.value[0]]}: ${numeric(p.value[2])}% retained`;
        },
      };
      option.series = [
        {
          type: "heatmap",
          data: spec.rows.map((r) => [
            periods.indexOf(Number(r.period)),
            cohorts.indexOf(String(r.name)),
            Number(r.value),
          ]),
          itemStyle: { borderWidth: 3, borderColor: dark ? "#18232e" : "#fff" },
          emphasis: { itemStyle: { borderColor: "#2f6fed" } },
        },
      ];
    }
    if (spec.kind === "scatter") {
      const escape = (v: unknown) =>
        String(v).replace(
          /[&<>"']/g,
          (c) =>
            ({
              "&": "&amp;",
              "<": "&lt;",
              ">": "&gt;",
              '"': "&quot;",
              "'": "&#39;",
            })[c]!,
        );
      option.legend = { show: false };
      option.xAxis = {
        type: "value",
        name: "Days in stage",
        nameLocation: "middle",
        nameGap: 26,
        axisLabel: { color: ink, fontSize: 10 },
        splitLine: { lineStyle: { color: border, type: "dashed" } },
      };
      option.tooltip = {
        trigger: "item",
        formatter: (input: unknown) => {
          const p = input as { data: { name: string; value: number[] } };
          return `${escape(p.data.name)}<br/>Stage age: ${numeric(p.data.value[0], 0)} days<br/>Exposure: £${numeric(p.data.value[1])}`;
        },
      };
      option.series = [
        {
          type: "scatter",
          symbolSize: 7,
          itemStyle: { opacity: 0.65 },
          data: spec.rows.map((r) => ({
            id: r.id,
            name: String(r.name),
            value: [Number(r.age), Number(r.value)],
          })),
        },
      ];
    }
    chart.setOption(option);
    if (onSelect)
      chart.on("click", (p) => onSelect(String((p.data as Row)?.id || p.name)));
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [spec, theme, onSelect]);
  return (
    <div
      ref={ref}
      className="chart"
      role="img"
      aria-label={`${spec.title}. ${spec.unit}. Exact data available in the table below.`}
    />
  );
}
