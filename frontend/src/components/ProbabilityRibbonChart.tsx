"use client"
import React from 'react'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

interface ProbabilityRibbonChartProps {
  data: { time: string, prob: number, upper: number, lower: number }[]
}

export function ProbabilityRibbonChart({ data }: ProbabilityRibbonChartProps) {
  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <XAxis dataKey="time" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
          <YAxis stroke="#888888" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `${(value * 100).toFixed(0)}%`} />
          <Tooltip 
            contentStyle={{ backgroundColor: 'hsl(var(--background))', borderColor: 'hsl(var(--border))' }}
            itemStyle={{ color: 'hsl(var(--foreground))' }}
          />
          {/* We'd use an AreaChart with custom gradients for proper uncertainty ribbons, using Line for simplicity here */}
          <Line type="monotone" dataKey="prob" stroke="#3b82f6" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="upper" stroke="#3b82f6" strokeWidth={1} strokeDasharray="3 3" dot={false} opacity={0.5} />
          <Line type="monotone" dataKey="lower" stroke="#3b82f6" strokeWidth={1} strokeDasharray="3 3" dot={false} opacity={0.5} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
