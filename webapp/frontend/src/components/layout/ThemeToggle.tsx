"use client";

import { IconButton, ListItemIcon, ListItemText, Menu, MenuItem, Tooltip } from "@mui/material";
import { useColorScheme } from "@mui/material/styles";
import { IconCheck, IconDeviceDesktop, IconMoon, IconSun } from "@tabler/icons-react";
import { useState } from "react";

const MODES = [
  { value: "light", label: "Sáng", icon: IconSun },
  { value: "dark", label: "Tối", icon: IconMoon },
  { value: "system", label: "Theo hệ thống", icon: IconDeviceDesktop },
] as const;

export function ThemeToggle() {
  const { mode, systemMode, setMode } = useColorScheme();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const resolved = mode === "system" ? systemMode : mode;
  const CurrentIcon = resolved === "dark" ? IconMoon : IconSun;

  return (
    <>
      <Tooltip title="Giao diện sáng/tối">
        <IconButton aria-label="Đổi giao diện sáng/tối" onClick={(e) => setAnchor(e.currentTarget)} sx={{ width: 44, height: 44 }}>
          <CurrentIcon size={20} stroke={1.7} />
        </IconButton>
      </Tooltip>
      <Menu anchorEl={anchor} open={anchor !== null} onClose={() => setAnchor(null)}>
        {MODES.map(({ value, label, icon: ModeIcon }) => (
          <MenuItem
            key={value}
            selected={mode === value}
            onClick={() => {
              setMode(value);
              setAnchor(null);
            }}
          >
            <ListItemIcon>
              <ModeIcon size={18} aria-hidden />
            </ListItemIcon>
            <ListItemText>{label}</ListItemText>
            {mode === value && <IconCheck size={16} aria-label="Đang chọn" />}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
