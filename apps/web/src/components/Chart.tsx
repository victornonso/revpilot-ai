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
import { ChartSpec, numeric } from "@/lib/api";
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
    chart.setOption(option);
    if (onSelect) chart.on("click", (p) => onSelect(p.name));
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
